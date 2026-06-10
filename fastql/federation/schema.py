"""Apollo Federation v2 schema construction and entity resolution."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any, TypeVar, overload

from fastql.context import Info
from fastql.federation.directives import federation_directives
from fastql.federation.sdl import print_federated_schema
from fastql.language import ast
from fastql.types import (
    Argument,
    Field,
    ListType,
    NonNull,
    ObjectType,
    ScalarType,
    Schema as CoreSchema,
    String,
    UnionType,
)

ReferenceResolver = Callable[..., Any]
ResolverType = TypeVar("ResolverType", bound=ReferenceResolver)

_reference_resolvers: dict[str, ReferenceResolver] = {}


@overload
def reference_resolver(entity: type, resolver: ResolverType) -> ResolverType: ...


@overload
def reference_resolver(entity: type) -> Callable[[ResolverType], ResolverType]: ...


def reference_resolver(
    entity: type, resolver: ResolverType | None = None
) -> ResolverType | Callable[[ResolverType], ResolverType]:
    """Register the resolver used for representations of ``entity``.

    The function supports direct and decorator forms::

        reference_resolver(Product, resolve_product)

        @reference_resolver(Product)
        def resolve_product(id: str) -> Product: ...
    """
    type_name = _entity_name(entity)

    def register(candidate: ResolverType) -> ResolverType:
        _reference_resolvers[type_name] = candidate
        return candidate

    if resolver is not None:
        return register(resolver)
    return register


register_reference = reference_resolver


def clear_reference_resolvers() -> None:
    """Clear process-wide reference resolvers, primarily for test isolation."""
    _reference_resolvers.clear()


class Schema(CoreSchema):
    """A core FastQL schema augmented as a Federation v2 subgraph."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.directives = {
            **self.directives,
            **federation_directives(),
        }
        self._install_federation_support()

    def _install_federation_support(self) -> None:
        entities = [
            type_
            for type_ in self.type_map.values()
            if isinstance(type_, ObjectType) and _is_entity(type_)
        ]
        service_type = ObjectType(
            name="_Service",
            fields={"sdl": Field(NonNull(String))},
        )
        self.query.fields["_service"] = Field(
            NonNull(service_type),
            resolver=_resolve_service,
        )

        support_types: list[Any] = [service_type]
        if entities:
            any_type = ScalarType(
                name="_Any",
                serialize=_identity,
                parse_value=_parse_any_value,
                parse_literal=_parse_any_literal,
            )
            entity_type = UnionType(
                name="_Entity",
                types=entities,
                resolve_type=_resolve_entity_type,
            )
            self.query.fields["_entities"] = Field(
                NonNull(ListType(entity_type)),
                args={
                    "representations": Argument(
                        NonNull(ListType(NonNull(any_type)))
                    )
                },
                resolver=_resolve_entities,
            )
            support_types.extend((any_type, entity_type))

        self.types.extend(support_types)
        self._initialize_type_map()


def _entity_name(entity: type) -> str:
    definition = getattr(entity, "__fastql_type__", None)
    name = getattr(definition, "name", None)
    if not name:
        raise TypeError("Reference resolver entity must be decorated with @Type")
    return name


def _is_entity(type_: ObjectType) -> bool:
    return any(
        getattr(directive, "name", None) == "key"
        for directive in type_.directives
    )


def _identity(value: Any) -> Any:
    return value


def _parse_any_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        raise TypeError("_Any representations must be objects")
    return dict(value)


def _parse_any_literal(node: ast.ValueNode) -> Any:
    if isinstance(node, ast.ObjectValueNode):
        return {
            field.name.value: _parse_any_literal(field.value)
            for field in node.fields
        }
    if isinstance(node, ast.ListValueNode):
        return [_parse_any_literal(value) for value in node.values]
    if isinstance(node, ast.IntValueNode):
        return int(node.value)
    if isinstance(node, ast.FloatValueNode):
        return float(node.value)
    if isinstance(node, ast.StringValueNode):
        return node.value
    if isinstance(node, ast.BooleanValueNode):
        return node.value
    if isinstance(node, ast.NullValueNode):
        return None
    if isinstance(node, ast.EnumValueNode):
        return node.value
    raise TypeError("Unsupported _Any literal")


def _resolve_service(info: Info) -> dict[str, str]:
    return {"sdl": print_federated_schema(info.schema)}


def _resolve_entity_type(value: Any) -> str | None:
    if isinstance(value, Mapping):
        typename = value.get("__typename")
        return typename if isinstance(typename, str) else None
    definition = getattr(type(value), "__fastql_type__", None)
    return getattr(definition, "name", None)


async def _resolve_entities(
    representations: list[dict[str, Any]], info: Info
) -> list[Any | None]:
    results: list[Any | None] = []
    for representation in representations:
        type_name = representation.get("__typename")
        resolver = _reference_resolvers.get(type_name)
        if resolver is None:
            results.append(None)
            continue
        key_fields = {
            name: value
            for name, value in representation.items()
            if name != "__typename"
        }
        result = _invoke_reference_resolver(resolver, key_fields, info)
        if inspect.isawaitable(result):
            result = await result
        results.append(result)
    return results


def _invoke_reference_resolver(
    resolver: ReferenceResolver,
    key_fields: dict[str, Any],
    info: Info,
) -> Any:
    signature = inspect.signature(resolver)
    kwargs: dict[str, Any] = {}
    accepts_extra = False
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            accepts_extra = True
        elif parameter.name == "info":
            kwargs[parameter.name] = info
        elif parameter.name == "representation":
            kwargs[parameter.name] = key_fields
        elif parameter.name in key_fields:
            kwargs[parameter.name] = key_fields[parameter.name]
    if accepts_extra:
        kwargs.update(
            {
                name: value
                for name, value in key_fields.items()
                if name not in kwargs
            }
        )
    return resolver(**kwargs)


__all__ = [
    "Schema",
    "clear_reference_resolvers",
    "reference_resolver",
    "register_reference",
]
