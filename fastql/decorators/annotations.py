"""Python annotation to GraphQL type-reference resolution."""

from __future__ import annotations

import collections.abc as _cabc
import sys
import types
import typing
from dataclasses import dataclass
from enum import Enum as PythonEnum
from typing import AbstractSet, Any, ForwardRef, TypeVar, get_args, get_origin

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

#: Async-stream container origins (subscription resolvers). The GraphQL field
#: type is the *yielded* type, so these unwrap to their first type argument.
_ASYNC_STREAM_ORIGINS = (
    _cabc.AsyncGenerator,
    _cabc.AsyncIterator,
    _cabc.AsyncIterable,
)
_ASYNC_STREAM_PREFIXES = (
    "AsyncGenerator",
    "AsyncIterator",
    "AsyncIterable",
    "typing.AsyncGenerator",
    "typing.AsyncIterator",
    "typing.AsyncIterable",
)


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


@dataclass(frozen=True)
class TypeVarRef:
    """Placeholder for a generic ``TypeVar`` inside a generic type's field.

    Synthesis (:mod:`fastql.schema_builder`) replaces it with the concrete named
    type bound to ``name`` at each parametrization site.
    """

    name: str


@dataclass(frozen=True)
class GenericTypeReference:
    """A reference to ``Template[arg, ...]`` resolved to a concrete type at build."""

    template: Any
    args: tuple[Any, ...]
    module: str | None = None


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
    type_params: AbstractSet[str] = frozenset(),
) -> Any:
    """Resolve a Python type hint into a GraphQL type reference.

    Bare hints are non-null by default. ``Optional`` / ``X | None`` removes only
    the outer non-null wrapper, while list elements remain non-null unless they
    are explicitly optional. ``type_params`` names the in-scope ``TypeVar`` s of a
    generic type; matching hints become :class:`TypeVarRef` placeholders.
    """

    resolved = _resolve_type_hint(
        hint, module=module, required=required, type_params=type_params
    )
    return resolved


def _resolve_type_hint(
    hint: Any, *, module: str | None, required: bool, type_params: AbstractSet[str]
) -> Any:
    if isinstance(hint, TypeVar):
        return _wrap(TypeVarRef(hint.__name__), required)
    if isinstance(hint, str):
        return _resolve_string_hint(
            hint, module=module, required=required, type_params=type_params
        )
    if isinstance(hint, ForwardRef):
        name = hint.__forward_arg__
        if name in type_params:
            return _wrap(TypeVarRef(name), required)
        return _wrap(TypeReference(name, module), required)

    origin = get_origin(hint)
    args = get_args(hint)

    if origin is typing.Annotated:
        return _resolve_type_hint(
            args[0], module=module, required=required, type_params=type_params
        )

    if origin in _ASYNC_STREAM_ORIGINS:
        inner = args[0] if args else Any
        return _resolve_type_hint(
            inner, module=module, required=required, type_params=type_params
        )

    if origin in (typing.Union, types.UnionType) or isinstance(hint, types.UnionType):
        union_args = args or get_args(hint)
        non_none = [arg for arg in union_args if arg is not NoneType]
        if len(non_none) == 1 and len(non_none) != len(union_args):
            return _resolve_type_hint(
                non_none[0], module=module, required=False, type_params=type_params
            )

    if origin is not None and getattr(origin, "__fastql_generic__", None) is not None and args:
        ref = GenericTypeReference(origin.__fastql_generic__, tuple(args), module)
        return _wrap(ref, required)

    if origin in (list, typing.List):
        inner = args[0] if args else Any
        return _wrap(
            ListType(
                _resolve_type_hint(
                    inner, module=module, required=True, type_params=type_params
                )
            ),
            required,
        )

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


def _resolve_string_hint(
    hint: str, *, module: str | None, required: bool, type_params: AbstractSet[str]
) -> Any:
    text = hint.strip()
    if (text.startswith("'") and text.endswith("'")) or (
        text.startswith('"') and text.endswith('"')
    ):
        text = text[1:-1]

    for prefix in _ASYNC_STREAM_PREFIXES:
        if text.startswith(prefix + "[") and text.endswith("]"):
            inner = text[len(prefix) + 1 : -1]
            yielded = _first_type_arg(inner).strip()
            return _resolve_string_hint(
                yielded, module=module, required=required, type_params=type_params
            )

    if text.endswith(" | None"):
        return _resolve_string_hint(
            text[: -len(" | None")], module=module, required=False, type_params=type_params
        )
    if text.startswith("Optional[") and text.endswith("]"):
        return _resolve_string_hint(
            text[len("Optional[") : -1], module=module, required=False, type_params=type_params
        )
    if text.startswith("typing.Optional[") and text.endswith("]"):
        return _resolve_string_hint(
            text[len("typing.Optional[") : -1], module=module, required=False,
            type_params=type_params,
        )
    if (text.startswith("list[") or text.startswith("List[")) and text.endswith("]"):
        inner = text[text.index("[") + 1 : -1]
        inner_ref = _resolve_string_hint(
            inner, module=module, required=True, type_params=type_params
        )
        return _wrap(ListType(inner_ref), required)

    if text in type_params:
        return _wrap(TypeVarRef(text), required)

    if text.endswith("]") and "[" in text:
        generic = _string_generic_reference(text, module)
        if generic is not None:
            return _wrap(generic, required)

    scalar = _scalar_for_hint(text)
    if scalar is not None:
        return _wrap(scalar, required)
    return _wrap(TypeReference(text, module), required)


def _string_generic_reference(text: str, module: str | None) -> "GenericTypeReference | None":
    """Build a :class:`GenericTypeReference` from a ``Name[arg, ...]`` string."""
    base = text[: text.index("[")].strip()
    cls = _lookup_name(base, module)
    template = getattr(cls, "__fastql_generic__", None) if cls is not None else None
    if template is None:
        return None
    inner = text[text.index("[") + 1 : -1]
    arg_texts = [part.strip() for part in _split_top_level(inner)]
    args = tuple(_lookup_name(part, module) or part for part in arg_texts)
    return GenericTypeReference(template, args, module)


def _lookup_name(name: str, module: str | None) -> Any:
    mod = sys.modules.get(module or "")
    return getattr(mod, name, None) if mod is not None else None


def _split_top_level(text: str) -> list[str]:
    """Split a generic's inner text on top-level commas."""
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [part for part in parts if part.strip()]


def _first_type_arg(text: str) -> str:
    """Return the first top-level type argument from a generic's inner text."""
    depth = 0
    for index, char in enumerate(text):
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
        elif char == "," and depth == 0:
            return text[:index]
    return text


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


__all__ = [
    "TypeReference",
    "TypeVarRef",
    "GenericTypeReference",
    "resolve_type_hint",
    "unwrap_non_null",
]
