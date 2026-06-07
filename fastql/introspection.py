"""The GraphQL introspection type graph and root meta-fields.

Builds the standard ``__Schema`` / ``__Type`` / ``__Field`` / ``__InputValue`` /
``__EnumValue`` / ``__Directive`` types (plus the ``__TypeKind`` and
``__DirectiveLocation`` enums) as ordinary FastQL IR, with resolvers that read
the FastQL type IR. :func:`introspection_root_fields` returns the ``__schema``
and ``__type`` fields that ``build_schema`` injects onto the query root.
``__typename`` is handled directly by the executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastql.types import (
    Argument,
    EnumType,
    Field,
    InputObjectType,
    InterfaceType,
    ListType,
    NonNull,
    ObjectType,
    ScalarType,
    UnionType,
)
from fastql.types.scalars import Boolean, String

# --- enums -------------------------------------------------------------------

__TypeKind = EnumType.from_names(
    "__TypeKind",
    [
        "SCALAR",
        "OBJECT",
        "INTERFACE",
        "UNION",
        "ENUM",
        "INPUT_OBJECT",
        "LIST",
        "NON_NULL",
    ],
)

__DirectiveLocation = EnumType.from_names(
    "__DirectiveLocation",
    [
        "QUERY",
        "MUTATION",
        "SUBSCRIPTION",
        "FIELD",
        "FRAGMENT_DEFINITION",
        "FRAGMENT_SPREAD",
        "INLINE_FRAGMENT",
        "VARIABLE_DEFINITION",
        "SCHEMA",
        "SCALAR",
        "OBJECT",
        "FIELD_DEFINITION",
        "ARGUMENT_DEFINITION",
        "INTERFACE",
        "UNION",
        "ENUM",
        "ENUM_VALUE",
        "INPUT_OBJECT",
        "INPUT_FIELD_DEFINITION",
    ],
)


# --- wrappers carrying a field/value name alongside its IR -------------------


@dataclass
class _NamedField:
    name: str
    field: Any


@dataclass
class _NamedInputValue:
    name: str
    value: Any  # Argument or InputField


@dataclass
class _NamedEnumValue:
    name: str
    value: Any  # EnumValue


# --- introspection object types (fields wired after creation) ---------------

__Type = ObjectType("__Type", fields={})
__Field = ObjectType("__Field", fields={})
__InputValue = ObjectType("__InputValue", fields={})
__EnumValue = ObjectType("__EnumValue", fields={})
__Schema = ObjectType("__Schema", fields={})
__Directive = ObjectType("__Directive", fields={})

_WRAPPERS = (NonNull, ListType)


def _type_kind(parent):
    if isinstance(parent, NonNull):
        return "NON_NULL"
    if isinstance(parent, ListType):
        return "LIST"
    return parent.kind.value


def _type_name(parent):
    if isinstance(parent, _WRAPPERS):
        return None
    return parent.name


def _type_description(parent):
    if isinstance(parent, _WRAPPERS):
        return None
    return getattr(parent, "description", None)


def _type_fields(parent, includeDeprecated=False):
    if not isinstance(parent, (ObjectType, InterfaceType)):
        return None
    out = []
    for name, field in parent.fields.items():
        if name.startswith("__"):
            continue
        if field.deprecation_reason and not includeDeprecated:
            continue
        out.append(_NamedField(name, field))
    return out


def _type_interfaces(parent):
    if isinstance(parent, ObjectType):
        return list(parent.interfaces)
    if isinstance(parent, InterfaceType):
        return []
    return None


def _type_possible_types(parent):
    if isinstance(parent, UnionType):
        return list(parent.types)
    return None


def _type_enum_values(parent, includeDeprecated=False):
    if not isinstance(parent, EnumType):
        return None
    out = []
    for name, enum_value in parent.values.items():
        if enum_value.deprecation_reason and not includeDeprecated:
            continue
        out.append(_NamedEnumValue(name, enum_value))
    return out


def _type_input_fields(parent):
    if not isinstance(parent, InputObjectType):
        return None
    return [_NamedInputValue(name, f) for name, f in parent.fields.items()]


def _build_types() -> None:
    nn_bool = NonNull(Boolean)
    nn_string = NonNull(String)

    __Type.fields.update(
        {
            "kind": Field(NonNull(__TypeKind), resolver=_type_kind),
            "name": Field(String, resolver=_type_name),
            "description": Field(String, resolver=_type_description),
            "fields": Field(
                ListType(NonNull(__Field)),
                args={"includeDeprecated": Argument(Boolean, default_value=False)},
                resolver=_type_fields,
            ),
            "interfaces": Field(ListType(NonNull(__Type)), resolver=_type_interfaces),
            "possibleTypes": Field(
                ListType(NonNull(__Type)), resolver=_type_possible_types
            ),
            "enumValues": Field(
                ListType(NonNull(__EnumValue)),
                args={"includeDeprecated": Argument(Boolean, default_value=False)},
                resolver=_type_enum_values,
            ),
            "inputFields": Field(
                ListType(NonNull(__InputValue)), resolver=_type_input_fields
            ),
            "ofType": Field(__Type, resolver=lambda parent: getattr(parent, "of_type", None)),
            "specifiedByURL": Field(
                String, resolver=lambda parent: getattr(parent, "specified_by_url", None)
            ),
        }
    )

    __Field.fields.update(
        {
            "name": Field(nn_string, resolver=lambda parent: parent.name),
            "description": Field(String, resolver=lambda parent: parent.field.description),
            "args": Field(
                NonNull(ListType(NonNull(__InputValue))),
                resolver=lambda parent: [
                    _NamedInputValue(n, a) for n, a in parent.field.args.items()
                ],
            ),
            "type": Field(NonNull(__Type), resolver=lambda parent: parent.field.type),
            "isDeprecated": Field(
                nn_bool, resolver=lambda parent: bool(parent.field.deprecation_reason)
            ),
            "deprecationReason": Field(
                String, resolver=lambda parent: parent.field.deprecation_reason
            ),
        }
    )

    __InputValue.fields.update(
        {
            "name": Field(nn_string, resolver=lambda parent: parent.name),
            "description": Field(
                String, resolver=lambda parent: getattr(parent.value, "description", None)
            ),
            "type": Field(NonNull(__Type), resolver=lambda parent: parent.value.type),
            "defaultValue": Field(String, resolver=_input_default_value),
            "isDeprecated": Field(
                nn_bool,
                resolver=lambda parent: bool(
                    getattr(parent.value, "deprecation_reason", None)
                ),
            ),
            "deprecationReason": Field(
                String,
                resolver=lambda parent: getattr(parent.value, "deprecation_reason", None),
            ),
        }
    )

    __EnumValue.fields.update(
        {
            "name": Field(nn_string, resolver=lambda parent: parent.name),
            "description": Field(
                String, resolver=lambda parent: parent.value.description
            ),
            "isDeprecated": Field(
                nn_bool, resolver=lambda parent: bool(parent.value.deprecation_reason)
            ),
            "deprecationReason": Field(
                String, resolver=lambda parent: parent.value.deprecation_reason
            ),
        }
    )

    __Schema.fields.update(
        {
            "description": Field(
                String, resolver=lambda parent: getattr(parent, "description", None)
            ),
            "types": Field(
                NonNull(ListType(NonNull(__Type))),
                resolver=lambda parent: list(parent.type_map.values()),
            ),
            "queryType": Field(NonNull(__Type), resolver=lambda parent: parent.query),
            "mutationType": Field(__Type, resolver=lambda parent: parent.mutation),
            "subscriptionType": Field(
                __Type, resolver=lambda parent: parent.subscription
            ),
            "directives": Field(
                NonNull(ListType(NonNull(__Directive))),
                resolver=lambda parent: list(parent.directives.values()),
            ),
        }
    )

    __Directive.fields.update(
        {
            "name": Field(nn_string, resolver=lambda parent: parent.name),
            "description": Field(String, resolver=lambda parent: parent.description),
            "locations": Field(
                NonNull(ListType(NonNull(__DirectiveLocation))),
                resolver=lambda parent: list(parent.locations),
            ),
            "args": Field(
                NonNull(ListType(NonNull(__InputValue))),
                resolver=lambda parent: [
                    _NamedInputValue(n, a) for n, a in parent.args.items()
                ],
            ),
            "isRepeatable": Field(
                nn_bool, resolver=lambda parent: parent.is_repeatable
            ),
        }
    )


def _input_default_value(parent):
    value = getattr(parent.value, "default_value", None)
    return None if value is None else str(value)


_build_types()


def introspection_root_fields() -> dict[str, Field]:
    """The ``__schema`` and ``__type`` meta-fields for the query root."""
    return {
        "__schema": Field(NonNull(__Schema), resolver=lambda info: info.schema),
        "__type": Field(
            __Type,
            args={"name": Argument(NonNull(String))},
            resolver=lambda name, info: info.schema.type_map.get(name),
        ),
    }


__all__ = ["introspection_root_fields"]
