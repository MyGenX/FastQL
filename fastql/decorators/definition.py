"""Shared compiler for class-shaped GraphQL definitions."""

from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass
from typing import Any, Callable, get_args, get_origin

from fastql.context import injected_parameter_names
from fastql.decorators.annotations import resolve_type_hint
from fastql.decorators.construct import DefaultFactory, _MISSING, apply_constructor
from fastql.decorators.field import Argument as ArgumentSpec
from fastql.decorators.field import FieldSpec, _UNSET
from fastql.decorators.registry import default_registry
from fastql.types import (
    Argument as IRArgument,
    Field as IRField,
    InputField,
    InputObjectType,
    InterfaceType,
    ObjectType,
)


@dataclass(frozen=True)
class DefinitionSpec:
    kind: str
    python_type: type
    name: str
    description: str | None = None
    interfaces: tuple[Any, ...] = ()


@dataclass(eq=False)
class GenericTemplate:
    """A deferred ``Generic[T]`` type, concretized per parametrization at build time.

    ``fields`` holds the collected IR fields with :class:`TypeVarRef` placeholders in
    type-variable positions; ``base_name``/``name_template`` drive synthetic naming.
    """

    kind: str
    python_type: type
    base_name: str
    name_template: str | None
    description: str | None
    interfaces: tuple[Any, ...]
    type_param_names: tuple[str, ...]
    fields: dict[str, Any]


def decorate_definition(
    kind: str,
    target: type,
    *,
    name: str | None = None,
    description: str | None = None,
    interfaces: list[Any] | None = None,
    directives: list[Any] | None = None,
) -> type:
    gql_name = name or _default_name(kind, target)
    applied_directives = list(directives or ())
    spec = DefinitionSpec(
        kind=kind,
        python_type=target,
        name=gql_name,
        description=description,
        interfaces=tuple(interfaces or ()),
    )
    setattr(target, "__fastql_definition__", spec)

    type_param_names = tuple(
        getattr(param, "__name__", str(param))
        for param in getattr(target, "__parameters__", ())
    )
    if type_param_names:
        return _decorate_generic(
            kind, target, name, description, interfaces, type_param_names
        )

    if kind == "input":
        fields, data_fields = _collect_fields(target, input_position=True)
        type_ = InputObjectType(
            gql_name,
            fields=fields,
            description=description,
            python_type=target,
            directives=applied_directives,
        )
        apply_constructor(target, data_fields)
        default_registry.register_type(target, type_)
        return target

    fields, data_fields = _collect_fields(target, input_position=False)
    if kind == "interface":
        type_ = InterfaceType(
            gql_name, fields=fields, description=description, directives=applied_directives
        )
        default_registry.register_type(target, type_)
        return target

    if kind == "type":
        resolved_interfaces = [_resolve_interface(value) for value in interfaces or ()]
        inherited: dict[str, IRField] = {}
        for interface in resolved_interfaces:
            inherited.update(interface.fields)
        inherited.update(fields)
        type_ = ObjectType(
            gql_name,
            fields=inherited,
            interfaces=resolved_interfaces,
            description=description,
            directives=applied_directives,
        )
        apply_constructor(target, data_fields)
        default_registry.register_type(target, type_)
        return target

    operation = kind
    type_ = ObjectType(gql_name, fields=fields, description=description)
    default_registry.register_root(operation, target, type_)
    for field_name, field_def in fields.items():
        if field_def.resolver is None:
            continue
        params = list(inspect.signature(field_def.resolver).parameters)
        field_def.owner = target if params and params[0] == "self" else None
        default_registry.register_operation(
            operation, field_name, field_def, field_def.resolver
        )
    return target


def _decorate_generic(
    kind: str,
    target: type,
    name: str | None,
    description: str | None,
    interfaces: list[Any] | None,
    type_param_names: tuple[str, ...],
) -> type:
    """Register ``target`` as a generic template; concretization is deferred to build."""
    if kind not in ("type", "input", "interface"):
        raise TypeError(f"@{kind.title()} cannot be generic.")
    params = frozenset(type_param_names)
    fields, data_fields = _collect_fields(
        target, input_position=(kind == "input"), type_params=params
    )
    if name and "{" in name:
        base_name, name_template = target.__name__, name
    elif name:
        base_name, name_template = name, None
    else:
        base_name, name_template = target.__name__, None
    template = GenericTemplate(
        kind=kind,
        python_type=target,
        base_name=base_name,
        name_template=name_template,
        description=description,
        interfaces=tuple(interfaces or ()),
        type_param_names=type_param_names,
        fields=fields,
    )
    default_registry.generic_templates[target] = template
    setattr(target, "__fastql_generic__", template)
    if kind in ("type", "input"):
        apply_constructor(target, data_fields)
    return target


def _collect_fields(
    cls: type, *, input_position: bool, type_params: frozenset[str] = frozenset()
) -> tuple[dict[str, Any], list[tuple[str, Any]]]:
    fields: dict[str, Any] = {}
    data_fields: list[tuple[str, Any]] = []
    annotations = getattr(cls, "__annotations__", {})

    for python_name, raw_hint in annotations.items():
        hint, _ = _unwrap_annotated(raw_hint)
        raw = cls.__dict__.get(python_name, _MISSING)
        spec = raw if isinstance(raw, FieldSpec) else None
        graphql_name = spec.graphql_name if spec and spec.graphql_name else python_name
        field_type = (
            spec.type
            if spec is not None and spec.type is not None
            else resolve_type_hint(hint, module=cls.__module__, type_params=type_params)
        )

        if spec is not None and spec.private:
            # Excluded from the GraphQL schema; still a Python attribute if it is
            # a data field (so resolvers can read it at runtime).
            if not spec.is_computed:
                data_fields.append((python_name, _field_default(raw, spec)))
            continue

        if input_position:
            if spec is not None and (
                spec.resolver is not None
                or spec.extensions
                or spec.permission_classes
                or spec.arguments
            ):
                raise TypeError(
                    f"Input field {cls.__name__}.{python_name} uses output-only metadata"
                )
            default = _field_default(raw, spec)
            default_factory = (
                default.factory if isinstance(default, DefaultFactory) else None
            )
            fields[graphql_name] = InputField(
                field_type,
                default_value=(
                    None
                    if default is _MISSING or isinstance(default, DefaultFactory)
                    else default
                ),
                description=spec.description if spec else None,
                deprecation_reason=spec.deprecation_reason if spec else None,
                python_name=python_name,
                directives=list(spec.directives if spec else ()),
                graphql_name_explicit=bool(spec and spec.graphql_name),
                default_factory=default_factory,
            )
            data_fields.append((python_name, default))
            continue

        if spec is not None and spec.is_computed:
            fields[graphql_name] = _output_field(
                cls, python_name, field_type, spec, spec.resolver, type_params
            )
            continue

        fields[graphql_name] = IRField(
            field_type,
            description=spec.description if spec else None,
            deprecation_reason=spec.deprecation_reason if spec else None,
            python_name=python_name,
            directives=list(spec.directives if spec else ()),
            extensions=list(spec.extensions if spec else ()),
            permission_classes=list(spec.permission_classes if spec else ()),
            graphql_name_explicit=bool(spec and spec.graphql_name),
            external=bool(spec and spec.external),
        )
        data_fields.append((python_name, _field_default(raw, spec)))

    if not input_position:
        for python_name, value in cls.__dict__.items():
            if python_name in annotations or not isinstance(value, FieldSpec):
                continue
            if not value.is_computed:
                continue
            resolver = value.resolver
            return_hint = inspect.signature(resolver).return_annotation
            if return_hint is inspect.Signature.empty and value.type is None:
                raise TypeError(
                    f"Computed field {cls.__name__}.{python_name} needs a return type"
                )
            field_type = value.type or resolve_type_hint(
                return_hint, module=cls.__module__, type_params=type_params
            )
            graphql_name = value.graphql_name or python_name
            fields[graphql_name] = _output_field(
                cls, python_name, field_type, value, resolver, type_params
            )

    return fields, data_fields


def _output_field(
    cls, python_name, field_type, spec, resolver, type_params=frozenset()
) -> IRField:
    return IRField(
        field_type,
        args=_arguments_from_resolver(
            resolver, cls.__module__, spec.arguments, type_params
        ),
        resolver=resolver,
        description=spec.description,
        deprecation_reason=spec.deprecation_reason,
        python_name=python_name,
        directives=list(spec.directives),
        extensions=list(spec.extensions),
        permission_classes=list(spec.permission_classes),
        graphql_name_explicit=bool(spec.graphql_name),
        external=bool(getattr(spec, "external", False)),
    )


def _arguments_from_resolver(
    resolver: Callable[..., Any],
    module: str | None,
    overrides: dict[str, ArgumentSpec] | None = None,
    type_params: frozenset[str] = frozenset(),
) -> dict[str, IRArgument]:
    signature = inspect.signature(resolver)
    injected = injected_parameter_names(resolver)
    hints = _type_hints(resolver)
    args: dict[str, IRArgument] = {}
    for parameter in signature.parameters.values():
        if parameter.name in injected or parameter.name == "cls":
            continue
        if parameter.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            continue
        annotation = hints.get(parameter.name, parameter.annotation)
        if annotation is inspect.Signature.empty:
            raise TypeError(f"Argument {parameter.name} needs a type annotation")
        hint, metadata = _unwrap_annotated(annotation)
        if not isinstance(metadata, ArgumentSpec):
            metadata = None
        default_metadata = (
            parameter.default if isinstance(parameter.default, ArgumentSpec) else None
        )
        explicit = (overrides or {}).get(parameter.name)
        meta = explicit or metadata or default_metadata or ArgumentSpec()
        gql_name = meta.name or parameter.name
        if meta.default is not _UNSET:
            default = meta.default
        elif parameter.default is not inspect.Signature.empty and not isinstance(
            parameter.default, ArgumentSpec
        ):
            default = parameter.default
        else:
            default = None
        args[gql_name] = IRArgument(
            resolve_type_hint(hint, module=module, type_params=type_params),
            default_value=default,
            description=meta.description,
            deprecation_reason=meta.deprecation_reason,
            python_name=parameter.name,
            directives=list(meta.directives),
            graphql_name_explicit=bool(meta.name),
        )
    return args


def _type_hints(resolver) -> dict[str, Any]:
    try:
        return typing.get_type_hints(resolver, include_extras=True)
    except Exception:
        return {}


def _unwrap_annotated(hint: Any) -> tuple[Any, Any]:
    if get_origin(hint) is typing.Annotated:
        values = get_args(hint)
        metadata = next(
            (item for item in values[1:] if isinstance(item, ArgumentSpec)), None
        )
        return values[0], metadata
    return hint, None


def _field_default(raw: Any, spec: FieldSpec | None) -> Any:
    if spec is not None:
        if spec.default_factory is not None:
            return DefaultFactory(spec.default_factory)
        if spec.has_default:
            return spec.default_value
        return _MISSING
    return raw


def _resolve_interface(interface: Any) -> InterfaceType:
    if isinstance(interface, InterfaceType):
        return interface
    type_ = getattr(interface, "__fastql_type__", None)
    if isinstance(type_, InterfaceType):
        return type_
    raise TypeError(f"{interface!r} is not a registered FastQL interface")


def _default_name(kind: str, target: type) -> str:
    if kind in ("query", "mutation", "subscription"):
        return kind.title()
    return target.__name__


__all__ = ["DefinitionSpec", "GenericTemplate", "decorate_definition"]
