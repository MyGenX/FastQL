"""Class decorators for object, interface, and input-object types."""

from __future__ import annotations

from typing import Callable

from fastql.decorators.definition import decorate_definition


def _class_decorator(kind: str, cls=None, **options):
    def decorate(target: type) -> type:
        return decorate_definition(kind, target, **options)

    return decorate(cls) if cls is not None else decorate


def Type(
    cls: type | None = None, *, name=None, description=None, interfaces=None, directives=None
):
    return _class_decorator(
        "type",
        cls,
        name=name,
        description=description,
        interfaces=interfaces,
        directives=directives,
    )


def Interface(cls: type | None = None, *, name=None, description=None, directives=None):
    return _class_decorator(
        "interface", cls, name=name, description=description, directives=directives
    )


def Input(cls: type | None = None, *, name=None, description=None, directives=None):
    return _class_decorator(
        "input", cls, name=name, description=description, directives=directives
    )


__all__ = ["Input", "Interface", "Type"]
