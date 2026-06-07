"""Synthesize ``__init__`` / ``__repr__`` / ``__eq__`` for ``@Type`` classes.

A ``@Type`` defines only its data fields; this module gives those classes a
dataclass-style constructor (positional + keyword, honoring defaults) plus value
``repr`` and ``eq`` — but only for the dunder methods the class does not already
define itself.
"""

from __future__ import annotations

from typing import Any

_MISSING = object()


class DefaultFactory:
    def __init__(self, factory):
        self.factory = factory


def apply_constructor(cls: type, data_fields: list[tuple[str, Any]]) -> None:
    """Add synthesized dunder methods to ``cls`` for its ordered data fields.

    ``data_fields`` is a list of ``(attribute_name, default)`` in declaration
    order; use the :data:`_MISSING` sentinel for fields without a default.
    """
    names = [name for name, _ in data_fields]
    if "__init__" not in cls.__dict__:
        cls.__init__ = _make_init(cls, data_fields)
    if "__repr__" not in cls.__dict__:
        cls.__repr__ = _make_repr(names)
    if "__eq__" not in cls.__dict__:
        cls.__eq__ = _make_eq(names)


def _make_init(cls: type, data_fields: list[tuple[str, Any]]):
    params = ["self"]
    defaults: dict[str, Any] = {}
    seen_default = False
    for name, default in data_fields:
        if default is _MISSING:
            if seen_default:
                raise TypeError(
                    f"{cls.__name__}: non-default field {name!r} cannot follow a "
                    "field with a default."
                )
            params.append(name)
        else:
            seen_default = True
            defaults[name] = default
            if isinstance(default, DefaultFactory):
                params.append(f"{name}=_missing")
            else:
                params.append(f"{name}=_defaults[{name!r}]")

    lines = []
    for name, default in data_fields:
        if isinstance(default, DefaultFactory):
            lines.append(
                f"    if {name} is _missing:\n"
                f"        {name} = _defaults[{name!r}].factory()"
            )
        lines.append(f"    self.{name} = {name}")
    body = "\n".join(lines) or "    pass"
    source = f"def __init__({', '.join(params)}):\n{body}"
    namespace: dict[str, Any] = {"_defaults": defaults, "_missing": _MISSING}
    exec(source, namespace)  # noqa: S102 - generated from field names, like dataclasses
    init = namespace["__init__"]
    init.__qualname__ = f"{cls.__qualname__}.__init__"
    return init


def _make_repr(names: list[str]):
    def __repr__(self) -> str:
        inner = ", ".join(f"{name}={getattr(self, name, None)!r}" for name in names)
        return f"{type(self).__name__}({inner})"

    return __repr__


def _make_eq(names: list[str]):
    def __eq__(self, other: Any) -> Any:
        if other.__class__ is not self.__class__:
            return NotImplemented
        return all(
            getattr(self, name, None) == getattr(other, name, None) for name in names
        )

    return __eq__


__all__ = ["DefaultFactory", "apply_constructor"]
