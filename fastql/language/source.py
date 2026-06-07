"""The GraphQL ``Source`` wrapper and source-location utilities."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_NAME = "GraphQL request"


class Source:
    """A wrapper around a raw GraphQL document string.

    Pairing the body with a name (and keeping it alongside locations) lets errors
    point back at exactly where in the input they originated.
    """

    __slots__ = ("body", "name")

    def __init__(self, body: str, name: str = DEFAULT_NAME) -> None:
        if not isinstance(body, str):
            raise TypeError(f"Source body must be a string, got {type(body).__name__}.")
        self.body = body
        self.name = name

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Source(name={self.name!r})"


@dataclass(frozen=True)
class SourceLocation:
    """A 1-based line/column position within a :class:`Source`."""

    line: int
    column: int


def get_location(source: Source, position: int) -> SourceLocation:
    """Compute the 1-based line and column for a character offset in ``source``.

    Line terminators recognized: ``\\n``, ``\\r`` and ``\\r\\n`` (the latter counts
    as a single newline).
    """
    body = source.body
    line = 1
    column = 1
    i = 0
    n = len(body)
    limit = min(position, n)
    while i < limit:
        ch = body[i]
        if ch == "\r":
            line += 1
            column = 1
            # Treat "\r\n" as one line terminator.
            if i + 1 < n and body[i + 1] == "\n":
                i += 1
        elif ch == "\n":
            line += 1
            column = 1
        else:
            column += 1
        i += 1
    return SourceLocation(line=line, column=column)
