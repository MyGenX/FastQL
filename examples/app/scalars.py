"""Custom scalar: ``DateTime``.

A ``@Scalar`` turns a Python type into a GraphQL leaf with three hooks:

* ``serialize`` — Python value → JSON-safe output (here, an ISO-8601 string);
* ``parse_value`` — a value arriving through ``variables``;
* ``parse_literal`` — a value written inline in the query, received as an AST node.

``Post.created_at`` is typed as ``datetime`` and resolves through this scalar, and
``PostFilter.published_since`` accepts one as input.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastql import Scalar


@Scalar
class DateTime:
    """ISO-8601 timestamps, serialized as strings on the wire."""

    @staticmethod
    def serialize(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def parse_value(value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def parse_literal(node) -> datetime:
        # Inline literals arrive as AST value nodes carrying the raw text.
        return datetime.fromisoformat(node.value)


__all__ = ["DateTime"]
