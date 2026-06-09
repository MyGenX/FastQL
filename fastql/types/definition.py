"""Definitions for the FastQL type-system intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable


class TypeKind(str, Enum):
    """GraphQL named type categories."""

    SCALAR = "SCALAR"
    OBJECT = "OBJECT"
    INTERFACE = "INTERFACE"
    UNION = "UNION"
    ENUM = "ENUM"
    INPUT_OBJECT = "INPUT_OBJECT"


@dataclass
class ScalarType:
    """A scalar type with input/output coercion hooks."""

    name: str
    serialize: Callable[[Any], Any]
    parse_value: Callable[[Any], Any]
    parse_literal: Callable[[Any], Any]
    description: str | None = None
    specified_by_url: str | None = None
    directives: list[Any] = field(default_factory=list)
    kind: TypeKind = field(default=TypeKind.SCALAR, init=False)


@dataclass
class Argument:
    """An argument accepted by a field or directive."""

    type: Any
    default_value: Any = None
    description: str | None = None
    deprecation_reason: str | None = None
    python_name: str | None = None
    directives: list[Any] = field(default_factory=list)
    graphql_name_explicit: bool = False


@dataclass
class Field:
    """A field exposed by an object or interface type."""

    type: Any
    args: dict[str, Argument] = field(default_factory=dict)
    resolver: Callable[..., Any] | None = None
    description: str | None = None
    deprecation_reason: str | None = None
    python_name: str | None = None
    directives: list[Any] = field(default_factory=list)
    extensions: list[Any] = field(default_factory=list)
    permission_classes: list[Any] = field(default_factory=list)
    owner: type | None = None
    graphql_name_explicit: bool = False
    external: bool = False


@dataclass
class InputField:
    """A field on a GraphQL input object."""

    type: Any
    default_value: Any = None
    description: str | None = None
    deprecation_reason: str | None = None
    python_name: str | None = None
    directives: list[Any] = field(default_factory=list)
    graphql_name_explicit: bool = False
    default_factory: Callable[[], Any] | None = None


@dataclass
class ObjectType:
    """A GraphQL object type."""

    name: str
    fields: dict[str, Field]
    interfaces: list["InterfaceType"] = field(default_factory=list)
    description: str | None = None
    is_type_of: Callable[[Any], bool] | None = None
    directives: list[Any] = field(default_factory=list)
    kind: TypeKind = field(default=TypeKind.OBJECT, init=False)


@dataclass
class InterfaceType:
    """A GraphQL interface type."""

    name: str
    fields: dict[str, Field]
    description: str | None = None
    resolve_type: Callable[[Any], ObjectType | str | None] | None = None
    directives: list[Any] = field(default_factory=list)
    kind: TypeKind = field(default=TypeKind.INTERFACE, init=False)


@dataclass
class UnionType:
    """A GraphQL union type over object types."""

    name: str
    types: list[ObjectType]
    description: str | None = None
    resolve_type: Callable[[Any], ObjectType | str | None] | None = None
    directives: list[Any] = field(default_factory=list)
    kind: TypeKind = field(default=TypeKind.UNION, init=False)


@dataclass
class EnumValue:
    """A single GraphQL enum value."""

    value: Any = None
    description: str | None = None
    deprecation_reason: str | None = None
    python_name: str | None = None


@dataclass
class EnumType:
    """A GraphQL enum type."""

    name: str
    values: dict[str, EnumValue]
    description: str | None = None
    directives: list[Any] = field(default_factory=list)
    kind: TypeKind = field(default=TypeKind.ENUM, init=False)

    @classmethod
    def from_names(
        cls, name: str, values: Iterable[str], *, description: str | None = None
    ) -> "EnumType":
        return cls(
            name=name,
            values={value_name: EnumValue(value_name) for value_name in values},
            description=description,
        )


@dataclass
class InputObjectType:
    """A GraphQL input-object type."""

    name: str
    fields: dict[str, InputField]
    description: str | None = None
    python_type: type | None = None
    directives: list[Any] = field(default_factory=list)
    kind: TypeKind = field(default=TypeKind.INPUT_OBJECT, init=False)


@dataclass
class DirectiveDefinition:
    """A GraphQL directive definition."""

    name: str
    locations: list[str]
    args: dict[str, Argument] = field(default_factory=dict)
    description: str | None = None
    is_repeatable: bool = False


@dataclass(frozen=True)
class AppliedDirective:
    """Directive metadata attached to a schema definition."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
