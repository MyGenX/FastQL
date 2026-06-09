"""Enum decorator with per-member customization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum as PythonEnum
from typing import Any, Callable

from fastql.decorators.registry import default_registry
from fastql.types import EnumType, EnumValue


@dataclass(frozen=True)
class EnumValueConfig:
    """Per-member overrides, used as an enum member's value via :func:`enum_value`."""

    value: Any
    name: str | None = None
    description: str | None = None
    deprecation_reason: str | None = None


def enum_value(
    value: Any,
    *,
    name: str | None = None,
    description: str | None = None,
    deprecation_reason: str | None = None,
) -> EnumValueConfig:
    """Customize a single enum member.

        @Enum
        class Color(enum.Enum):
            RED = "red"
            GREEN = enum_value("green", deprecation_reason="use RED")
    """
    return EnumValueConfig(
        value=value,
        name=name,
        description=description,
        deprecation_reason=deprecation_reason,
    )


def Enum(
    cls: type[PythonEnum] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> type[PythonEnum] | Callable[[type[PythonEnum]], type[PythonEnum]]:
    """Register a Python ``Enum`` subclass as a GraphQL enum."""

    def decorate(target: type[PythonEnum]) -> type[PythonEnum]:
        if not issubclass(target, PythonEnum):
            raise TypeError("@Enum can only decorate enum.Enum subclasses")
        values: dict[str, EnumValue] = {}
        for member in target:
            raw = member.value
            if isinstance(raw, EnumValueConfig):
                gql_name = raw.name or member.name
                values[gql_name] = EnumValue(
                    value=raw.value,
                    description=raw.description,
                    deprecation_reason=raw.deprecation_reason,
                    python_name=member.name,
                )
            else:
                values[member.name] = EnumValue(member.value, python_name=member.name)
        type_ = EnumType(name or target.__name__, values=values, description=description)
        default_registry.register_type(target, type_)
        return target

    if cls is not None:
        return decorate(cls)
    return decorate


__all__ = ["Enum", "enum_value", "EnumValueConfig"]
