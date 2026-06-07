"""Enum decorator."""

from __future__ import annotations

from enum import Enum as PythonEnum
from typing import Callable

from fastql.decorators.registry import default_registry
from fastql.types import EnumType, EnumValue


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
        type_ = EnumType(
            name or target.__name__,
            values={
                member.name: EnumValue(member.value) for member in target
            },
            description=description,
        )
        default_registry.register_type(target, type_)
        return target

    if cls is not None:
        return decorate(cls)
    return decorate


__all__ = ["Enum"]
