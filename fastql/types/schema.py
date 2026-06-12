"""Schema container and type-map construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastql.types.definition import (
    Argument,
    DirectiveDefinition,
    EnumType,
    Field,
    InputField,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    UnionType,
)
from fastql.types.scalars import Boolean, Int, String
from fastql.types.wrappers import ListType, NonNull

NamedType = ScalarType | ObjectType | InterfaceType | UnionType | EnumType | InputObjectType


@dataclass(frozen=True)
class SchemaConfig:
    """Configuration applied while decorated definitions are compiled."""

    auto_camel_case: bool = True


@dataclass(init=False)
class Schema:
    """A GraphQL schema with root types, directives, and reachable named types."""

    query: ObjectType
    mutation: ObjectType | None = None
    subscription: ObjectType | None = None
    directives: dict[str, DirectiveDefinition] = field(default_factory=dict)
    types: list[NamedType] = field(default_factory=list)
    config: SchemaConfig = field(default_factory=SchemaConfig)
    extensions: list[Any] = field(default_factory=list)

    def __init__(
        self,
        query: Any,
        mutation: Any = None,
        subscription: Any = None,
        *,
        directives: dict[str, DirectiveDefinition] | None = None,
        types: list[NamedType] | None = None,
        config: SchemaConfig | None = None,
        extensions: list[Any] | None = None,
        registry: Any = None,
        _built: bool = False,
    ) -> None:
        if not _built and isinstance(query, type) and getattr(
            query, "__fastql_type__", None
        ) is not None:
            from fastql.schema_builder import build_schema

            compiled = build_schema(
                query,
                mutation=mutation,
                subscription=subscription,
                types=types,
                registry=registry,
                config=config or SchemaConfig(),
            )
            self.__dict__.update(compiled.__dict__)
            self.extensions = list(extensions or [])
            return
        self.query = query
        self.mutation = mutation
        self.subscription = subscription
        self.directives = directives or default_directives()
        self.types = list(types or [])
        self.config = config or SchemaConfig(auto_camel_case=False)
        self.extensions = list(extensions or [])
        self._initialize_type_map()

    def _initialize_type_map(self) -> None:
        if not self.directives:
            self.directives = default_directives()
        self.type_map: dict[str, NamedType] = {}
        for root in (self.query, self.mutation, self.subscription):
            if root is not None:
                self._collect_named_type(root)
        for type_ in self.types:
            self._collect_named_type(type_)

    def _collect_type_reference(self, type_: Any) -> None:
        if isinstance(type_, (NonNull, ListType)):
            self._collect_type_reference(type_.of_type)
            return
        self._collect_named_type(type_)

    def _collect_named_type(self, type_: Any) -> None:
        if not _is_named_type(type_):
            return
        existing = self.type_map.get(type_.name)
        if existing is not None:
            if existing is not type_:
                raise ValueError(f"Duplicate type name: {type_.name}")
            return
        self.type_map[type_.name] = type_
        if isinstance(type_, (ObjectType, InterfaceType)):
            for interface in getattr(type_, "interfaces", []):
                self._collect_named_type(interface)
            for field_def in type_.fields.values():
                self._collect_field(field_def)
        elif isinstance(type_, UnionType):
            for member in type_.types:
                self._collect_named_type(member)
        elif isinstance(type_, InputObjectType):
            for input_field in type_.fields.values():
                self._collect_input_field(input_field)

    def _collect_field(self, field_def: Field) -> None:
        self._collect_type_reference(field_def.type)
        for arg in field_def.args.values():
            self._collect_argument(arg)

    def _collect_argument(self, arg: Argument) -> None:
        self._collect_type_reference(arg.type)

    def _collect_input_field(self, input_field: InputField) -> None:
        self._collect_type_reference(input_field.type)


def default_directives() -> dict[str, DirectiveDefinition]:
    """Return the built-in directive definitions."""

    boolean_non_null = NonNull(Boolean)
    return {
        "include": DirectiveDefinition(
            name="include",
            locations=["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
            args={"if": Argument(boolean_non_null)},
            description="Directs the executor to include this selection only when true.",
        ),
        "skip": DirectiveDefinition(
            name="skip",
            locations=["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
            args={"if": Argument(boolean_non_null)},
            description="Directs the executor to skip this selection when true.",
        ),
        "deprecated": DirectiveDefinition(
            name="deprecated",
            locations=["FIELD_DEFINITION", "ARGUMENT_DEFINITION", "ENUM_VALUE"],
            args={"reason": Argument(String, default_value="No longer supported")},
            description="Marks an element as deprecated.",
        ),
        "defer": DirectiveDefinition(
            name="defer",
            locations=["FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
            args={
                "if": Argument(NonNull(Boolean), default_value=True),
                "label": Argument(String),
            },
            description=(
                "Delays delivery of the marked fragment to a later incremental "
                "payload over a streaming transport."
            ),
        ),
        "stream": DirectiveDefinition(
            name="stream",
            locations=["FIELD"],
            args={
                "if": Argument(NonNull(Boolean), default_value=True),
                "initialCount": Argument(NonNull(Int), default_value=0),
                "label": Argument(String),
            },
            description=(
                "Streams a list field: initial items are returned immediately and "
                "the rest arrive in later incremental payloads."
            ),
        ),
    }


def _is_named_type(type_: Any) -> bool:
    return isinstance(
        type_, (ScalarType, ObjectType, InterfaceType, UnionType, EnumType, InputObjectType)
    )


__all__ = ["NamedType", "Schema", "SchemaConfig", "default_directives"]
