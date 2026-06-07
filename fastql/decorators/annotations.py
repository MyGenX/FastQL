"""Python annotation to GraphQL type-reference resolution."""

from __future__ import annotations

import sys
import types
import typing
from dataclasses import dataclass
from enum import Enum as PythonEnum
from typing import Any, ForwardRef, get_args, get_origin

from fastql.types import (
    Boolean,
    Float,
    ID,
    InputObjectType,
    Int,
    ListType,
    NonNull,
    ObjectType,
    ScalarType,
    String,
)

NoneType = type(None)


@dataclass(frozen=True)
class TypeReference:
    """A lazily resolved named type reference."""

    name: str
    module: str | None = None

    def __call__(self) -> Any:
        module = sys.modules.get(self.module or "")
        if module is not None:
            value = getattr(module, self.name, None)
            if value is not None:
                return getattr(value, "__fastql_type__", value)
        raise LookupError(f"Unresolved GraphQL type reference: {self.name}")

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"TypeReference({self.name!r})"


_SCALAR_HINTS: dict[Any, ScalarType] = {
    int: Int,
    float: Float,
    str: String,
    bool: Boolean,
    "int": Int,
    "float": Float,
    "str": String,
    "bool": Boolean,
    "ID": ID,
}


def resolve_type_hint(
    hint: Any,
    *,
    module: str | None = None,
    required: bool = True,
) -> Any:
    """Resolve a Python type hint into a GraphQL type reference.

    Bare hints are non-null by default. ``Optional`` / ``X | None`` removes only
    the outer non-null wrapper, while list elements remain non-null unless they
    are explicitly optional.
    """

    resolved = _resolve_type_hint(hint, module=module, required=required)
    return resolved


def _resolve_type_hint(hint: Any, *, module: str | None, required: bool) -> Any:
    if isinstance(hint, str):
        return _resolve_string_hint(hint, module=module, required=required)
    if isinstance(hint, ForwardRef):
        return _wrap(TypeReference(hint.__forward_arg__, module), required)

    origin = get_origin(hint)
    args = get_args(hint)

    if origin is typing.Annotated:
        return _resolve_type_hint(args[0], module=module, required=required)

    if origin in (typing.Union, types.UnionType) or isinstance(hint, types.UnionType):
        union_args = args or get_args(hint)
        non_none = [arg for arg in union_args if arg is not NoneType]
        if len(non_none) == 1 and len(non_none) != len(union_args):
            return _resolve_type_hint(non_none[0], module=module, required=False)

    if origin in (list, typing.List):
        inner = args[0] if args else Any
        return _wrap(ListType(_resolve_type_hint(inner, module=module, required=True)), required)

    scalar = _scalar_for_hint(hint)
    if scalar is not None:
        return _wrap(scalar, required)

    registered = getattr(hint, "__fastql_type__", None)
    if registered is not None:
        return _wrap(registered, required)

    if isinstance(hint, type) and issubclass(hint, PythonEnum):
        registered = getattr(hint, "__fastql_type__", None)
        if registered is not None:
            return _wrap(registered, required)
        return _wrap(TypeReference(hint.__name__, hint.__module__), required)

    if isinstance(hint, (ScalarType, ObjectType, InputObjectType)):
        return _wrap(hint, required)

    if hint is Any:
        raise TypeError("Cannot infer a GraphQL type from typing.Any")

    name = getattr(hint, "__name__", None)
    if name:
        return _wrap(TypeReference(name, getattr(hint, "__module__", module)), required)
    raise TypeError(f"Cannot infer a GraphQL type from annotation {hint!r}")


def _resolve_string_hint(hint: str, *, module: str | None, required: bool) -> Any:
    text = hint.strip()
    if (text.startswith("'") and text.endswith("'")) or (
        text.startswith('"') and text.endswith('"')
    ):
        text = text[1:-1]

    if text.endswith(" | None"):
        return _resolve_string_hint(text[: -len(" | None")], module=module, required=False)
    if text.startswith("Optional[") and text.endswith("]"):
        return _resolve_string_hint(text[len("Optional[") : -1], module=module, required=False)
    if text.startswith("typing.Optional[") and text.endswith("]"):
        return _resolve_string_hint(
            text[len("typing.Optional[") : -1], module=module, required=False
        )
    if (text.startswith("list[") or text.startswith("List[")) and text.endswith("]"):
        inner = text[text.index("[") + 1 : -1]
        inner_ref = _resolve_string_hint(inner, module=module, required=True)
        return _wrap(ListType(inner_ref), required)

    scalar = _scalar_for_hint(text)
    if scalar is not None:
        return _wrap(scalar, required)
    return _wrap(TypeReference(text, module), required)


def _wrap(type_: Any, required: bool) -> Any:
    if required:
        return NonNull(type_)
    return type_


def _scalar_for_hint(hint: Any) -> ScalarType | None:
    for scalar in (Int, Float, String, Boolean, ID):
        if hint is scalar:
            return scalar
    try:
        return _SCALAR_HINTS.get(hint)
    except TypeError:
        return None


def unwrap_non_null(type_: Any) -> Any:
    """Return the nullable form of a type reference."""

    if isinstance(type_, NonNull):
        return type_.of_type
    return type_


__all__ = ["TypeReference", "resolve_type_hint", "unwrap_non_null"]
