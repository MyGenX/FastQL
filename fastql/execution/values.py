"""Input and output value coercion for execution.

Three input paths feed resolvers: variable values (raw Python in, coerced
against their declared types), argument literals (AST nodes coerced against the
argument type, substituting variables), and a shared leaf-serialization path for
turning resolver outputs back into scalar/enum response values.
"""

from __future__ import annotations

from enum import Enum as PythonEnum
from typing import Any

from fastql.errors import GraphQLError
from fastql.language import ast
from fastql.types import (
    EnumType,
    InputObjectType,
    ScalarType,
)
from fastql.types.scalars import BUILT_IN_SCALARS
from fastql.types.wrappers import ListType, NonNull

_UNSET = object()


# --- variables ---------------------------------------------------------------


def coerce_variable_values(
    schema: Any, operation: ast.OperationDefinitionNode, raw: dict[str, Any]
) -> dict[str, Any]:
    """Coerce raw input variables against their declared operation types."""
    coerced: dict[str, Any] = {}
    for var_def in operation.variable_definitions:
        name = var_def.variable.name.value
        type_ref = type_from_ast(schema, var_def.type)
        if name in raw:
            value = raw[name]
            if value is None:
                if isinstance(type_ref, NonNull):
                    raise GraphQLError(
                        f"Variable '${name}' of non-null type must not be null."
                    )
                coerced[name] = None
            else:
                coerced[name] = coerce_input_value(value, type_ref, f"${name}")
        elif var_def.default_value is not None:
            coerced[name] = value_from_ast(var_def.default_value, type_ref, {})
        elif isinstance(type_ref, NonNull):
            raise GraphQLError(
                f"Variable '${name}' of required type was not provided."
            )
    return coerced


def type_from_ast(schema: Any, type_node: ast.TypeNode) -> Any:
    if isinstance(type_node, ast.NonNullTypeNode):
        return NonNull(type_from_ast(schema, type_node.type))
    if isinstance(type_node, ast.ListTypeNode):
        return ListType(type_from_ast(schema, type_node.type))
    name = type_node.name.value
    named = schema.type_map.get(name) or BUILT_IN_SCALARS.get(name)
    if named is None:
        raise GraphQLError(f"Unknown type '{name}' in variable definition.")
    return named


# --- raw Python input coercion ----------------------------------------------


def coerce_input_value(value: Any, type_ref: Any, where: str) -> Any:
    if isinstance(type_ref, NonNull):
        if value is None:
            raise GraphQLError(f"Expected non-null value for {where}.")
        return coerce_input_value(value, type_ref.of_type, where)
    if value is None:
        return None
    if isinstance(type_ref, ListType):
        items = value if isinstance(value, (list, tuple)) else [value]
        return [coerce_input_value(item, type_ref.of_type, where) for item in items]
    if isinstance(type_ref, ScalarType):
        return type_ref.parse_value(value)
    if isinstance(type_ref, EnumType):
        if isinstance(value, str) and value in type_ref.values:
            return type_ref.values[value].value
        raise GraphQLError(f"Invalid enum value {value!r} for {where}.")
    if isinstance(type_ref, InputObjectType):
        if not isinstance(value, dict):
            raise GraphQLError(f"Expected an object for {where}.")
        return _coerce_input_object(value, type_ref, where)
    return value


def _coerce_input_object(value: dict, input_type: InputObjectType, where: str) -> Any:
    result: dict[str, Any] = {}
    for field_name, input_field in input_type.fields.items():
        python_name = input_field.python_name or field_name
        if field_name in value:
            result[python_name] = coerce_input_value(
                value[field_name], input_field.type, f"{where}.{field_name}"
            )
        elif getattr(input_field, "default_factory", None) is not None:
            result[python_name] = input_field.default_factory()
        elif getattr(input_field, "default_value", None) is not None:
            result[python_name] = input_field.default_value
        elif isinstance(input_field.type, NonNull):
            raise GraphQLError(
                f"Missing required input field {field_name!r} for {where}."
            )
    if input_type.python_type is not None:
        return input_type.python_type(**result)
    return result


# --- AST literal coercion ----------------------------------------------------


def coerce_argument_values(
    field_def: Any, field_node: ast.FieldNode, variable_values: dict[str, Any]
) -> dict[str, Any]:
    """Coerce a field's argument literals into Python values for the resolver."""
    arg_nodes = {arg.name.value: arg for arg in field_node.arguments}
    coerced: dict[str, Any] = {}
    for arg_name, arg_def in field_def.args.items():
        node = arg_nodes.get(arg_name)
        if node is None:
            if arg_def.default_value is not None:
                coerced[arg_def.python_name or arg_name] = arg_def.default_value
            elif isinstance(arg_def.type, NonNull):
                raise GraphQLError(f"Argument {arg_name!r} of required type is missing.")
            # otherwise omit so the resolver's own default applies
            continue
        value_node = node.value
        if isinstance(value_node, ast.VariableNode):
            var_name = value_node.name.value
            if var_name in variable_values:
                coerced[arg_def.python_name or arg_name] = variable_values[var_name]
            elif arg_def.default_value is not None:
                coerced[arg_def.python_name or arg_name] = arg_def.default_value
            continue
        coerced[arg_def.python_name or arg_name] = value_from_ast(
            value_node, arg_def.type, variable_values
        )
    return coerced


def value_from_ast(node: ast.ValueNode, type_ref: Any, variable_values: dict[str, Any]) -> Any:
    if isinstance(node, ast.VariableNode):
        return variable_values.get(node.name.value)
    if isinstance(type_ref, NonNull):
        value = value_from_ast(node, type_ref.of_type, variable_values)
        if value is None:
            raise GraphQLError("Expected non-null value but got null.")
        return value
    if isinstance(node, ast.NullValueNode):
        return None
    if isinstance(type_ref, ListType):
        if isinstance(node, ast.ListValueNode):
            return [
                value_from_ast(item, type_ref.of_type, variable_values)
                for item in node.values
            ]
        return [value_from_ast(node, type_ref.of_type, variable_values)]
    if isinstance(type_ref, ScalarType):
        return type_ref.parse_literal(node)
    if isinstance(type_ref, EnumType):
        if isinstance(node, ast.EnumValueNode) and node.value in type_ref.values:
            return type_ref.values[node.value].value
        raise GraphQLError(f"Invalid enum value for type {type_ref.name!r}.")
    if isinstance(type_ref, InputObjectType):
        if not isinstance(node, ast.ObjectValueNode):
            raise GraphQLError(f"Expected an input object for {type_ref.name!r}.")
        return _input_object_from_ast(node, type_ref, variable_values)
    return None


def _input_object_from_ast(node, input_type, variable_values) -> dict:
    provided = {f.name.value: f.value for f in node.fields}
    result: dict[str, Any] = {}
    for field_name, input_field in input_type.fields.items():
        python_name = input_field.python_name or field_name
        if field_name in provided:
            result[python_name] = value_from_ast(
                provided[field_name], input_field.type, variable_values
            )
        elif getattr(input_field, "default_factory", None) is not None:
            result[python_name] = input_field.default_factory()
        elif getattr(input_field, "default_value", None) is not None:
            result[python_name] = input_field.default_value
        elif isinstance(input_field.type, NonNull):
            raise GraphQLError(f"Missing required input field {field_name!r}.")
    if input_type.python_type is not None:
        return input_type.python_type(**result)
    return result


# --- output leaf serialization ----------------------------------------------


def complete_leaf_value(named_type: Any, value: Any) -> Any:
    if isinstance(named_type, ScalarType):
        return named_type.serialize(value)
    if isinstance(named_type, EnumType):
        if isinstance(value, PythonEnum):
            if value.name in named_type.values:
                return value.name
            for enum_name, enum_value in named_type.values.items():
                if getattr(enum_value, "python_name", None) == value.name:
                    return enum_name  # GraphQL name override via enum_value(name=...)
        for enum_name, enum_value in named_type.values.items():
            if enum_value.value == value or enum_name == value:
                return enum_name
        raise GraphQLError(
            f"Cannot serialize value {value!r} as enum {named_type.name!r}."
        )
    return value


__all__ = [
    "coerce_variable_values",
    "coerce_argument_values",
    "coerce_input_value",
    "value_from_ast",
    "complete_leaf_value",
    "type_from_ast",
]
