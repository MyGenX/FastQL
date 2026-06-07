"""Custom scalar decorator."""

from __future__ import annotations

from typing import Any, Callable

from fastql.decorators.registry import default_registry
from fastql.types import ScalarType


def Scalar(
    target: type | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    serialize: Callable[[Any], Any] | None = None,
    parse_value: Callable[[Any], Any] | None = None,
    parse_literal: Callable[[Any], Any] | None = None,
    specified_by_url: str | None = None,
) -> type | Callable[[type], type]:
    """Register a marker class as a custom GraphQL scalar."""

    def decorate(cls: type) -> type:
        serializer = serialize or getattr(cls, "serialize", None)
        value_parser = parse_value or getattr(cls, "parse_value", None) or serializer
        literal_parser = parse_literal or getattr(cls, "parse_literal", None) or value_parser
        if serializer is None or value_parser is None or literal_parser is None:
            raise TypeError("@Scalar requires serialize, parse_value, and parse_literal hooks")
        type_ = ScalarType(
            name or cls.__name__,
            serialize=serializer,
            parse_value=value_parser,
            parse_literal=literal_parser,
            description=description,
            specified_by_url=specified_by_url,
        )
        default_registry.register_type(cls, type_)
        return cls

    if target is not None:
        return decorate(target)
    return decorate


__all__ = ["Scalar"]
