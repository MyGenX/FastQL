"""Built-in GraphQL scalar types."""

from __future__ import annotations

from math import isfinite
from typing import Any

from fastql.errors import GraphQLError
from fastql.language import ast
from fastql.types.definition import ScalarType

_INT_MIN = -(2**31)
_INT_MAX = 2**31 - 1


class ScalarCoercionError(GraphQLError):
    """Raised when a scalar cannot coerce a provided value."""


def _coercion_error(type_name: str, value: Any) -> ScalarCoercionError:
    return ScalarCoercionError(f"Invalid {type_name} value: {value!r}")


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _coercion_error("Int", value)
    if value < _INT_MIN or value > _INT_MAX:
        raise _coercion_error("Int", value)
    return value


def _parse_int_literal(value: ast.ValueNode) -> int:
    if not isinstance(value, ast.IntValueNode):
        raise _coercion_error("Int", _literal_debug_value(value))
    return _coerce_int(int(value.value))


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _coercion_error("Float", value)
    coerced = float(value)
    if not isfinite(coerced):
        raise _coercion_error("Float", value)
    return coerced


def _parse_float_literal(value: ast.ValueNode) -> float:
    if not isinstance(value, (ast.IntValueNode, ast.FloatValueNode)):
        raise _coercion_error("Float", _literal_debug_value(value))
    return _coerce_float(float(value.value))


def _coerce_string(value: Any) -> str:
    if not isinstance(value, str):
        raise _coercion_error("String", value)
    return value


def _parse_string_literal(value: ast.ValueNode) -> str:
    if not isinstance(value, ast.StringValueNode):
        raise _coercion_error("String", _literal_debug_value(value))
    return value.value


def _coerce_boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise _coercion_error("Boolean", value)
    return value


def _parse_boolean_literal(value: ast.ValueNode) -> bool:
    if not isinstance(value, ast.BooleanValueNode):
        raise _coercion_error("Boolean", _literal_debug_value(value))
    return value.value


def _coerce_id(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise _coercion_error("ID", value)
    return str(value)


def _parse_id_literal(value: ast.ValueNode) -> str:
    if not isinstance(value, (ast.StringValueNode, ast.IntValueNode)):
        raise _coercion_error("ID", _literal_debug_value(value))
    return str(value.value)


def _literal_debug_value(value: ast.ValueNode) -> Any:
    return getattr(value, "value", value.__class__.__name__)


Int = ScalarType("Int", _coerce_int, _coerce_int, _parse_int_literal)
Float = ScalarType("Float", _coerce_float, _coerce_float, _parse_float_literal)
String = ScalarType("String", _coerce_string, _coerce_string, _parse_string_literal)
Boolean = ScalarType(
    "Boolean", _coerce_boolean, _coerce_boolean, _parse_boolean_literal
)
ID = ScalarType("ID", _coerce_id, _coerce_id, _parse_id_literal)

BUILT_IN_SCALARS: dict[str, ScalarType] = {
    scalar.name: scalar for scalar in (Int, Float, String, Boolean, ID)
}

__all__ = [
    "Boolean",
    "BUILT_IN_SCALARS",
    "Float",
    "ID",
    "Int",
    "ScalarCoercionError",
    "String",
]
