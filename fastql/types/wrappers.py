"""Wrapping types for GraphQL input and output positions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ListType:
    """A GraphQL list wrapper around another type reference."""

    of_type: Any

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"List({self.of_type!r})"


@dataclass(frozen=True)
class NonNull:
    """A GraphQL non-null wrapper.

    GraphQL disallows wrapping an already non-null type in another ``NonNull``.
    """

    of_type: Any

    def __post_init__(self) -> None:
        if isinstance(self.of_type, NonNull):
            raise TypeError("NonNull cannot wrap another NonNull type")

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"NonNull({self.of_type!r})"
