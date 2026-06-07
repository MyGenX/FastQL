"""Error types for FastQL.

This module defines :class:`GraphQLError`, the base for all spec-shaped errors,
and :class:`GraphQLSyntaxError`, raised by the lexer and parser. It is kept
intentionally small here; later layers (validation, execution) build on the same
base so every error can be serialized to the ``{message, locations, path}`` shape
required by the GraphQL response format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from fastql.language.source import Source, SourceLocation


class GraphQLError(Exception):
    """An error that can be reported in a GraphQL ``errors`` array.

    Carries an optional list of source ``locations`` and a response ``path`` so it
    can be formatted per the GraphQL specification.
    """

    def __init__(
        self,
        message: str,
        *,
        locations: Sequence["SourceLocation"] | None = None,
        path: Sequence[str | int] | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.locations: list["SourceLocation"] = list(locations) if locations else []
        self.path: list[str | int] | None = list(path) if path is not None else None
        self.original_error = original_error

    def formatted(self) -> dict[str, Any]:
        """Return the GraphQL response representation of this error."""
        out: dict[str, Any] = {"message": self.message}
        if self.locations:
            out["locations"] = [
                {"line": loc.line, "column": loc.column} for loc in self.locations
            ]
        if self.path is not None:
            out["path"] = list(self.path)
        return out

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ValidationError(GraphQLError):
    """A validation error produced while checking an operation against a schema."""


class GraphQLSyntaxError(GraphQLError):
    """A syntax error produced while lexing or parsing a GraphQL document."""

    def __init__(self, source: "Source", position: int, description: str) -> None:
        from fastql.language.source import get_location

        location = get_location(source, position)
        message = f"Syntax Error: {description}"
        super().__init__(message, locations=[location])
        self.source = source
        self.position = position
        self.description = description


__all__ = ["GraphQLError", "ValidationError", "GraphQLSyntaxError"]
