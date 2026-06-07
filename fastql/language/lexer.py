"""A hand-built lexer for the GraphQL executable language.

Produces a forward stream of :class:`Token` objects on demand. Insignificant
commas, whitespace, byte-order marks, and comments are skipped. Invalid input
raises :class:`~fastql.errors.GraphQLSyntaxError` carrying the offending position.
"""

from __future__ import annotations

from enum import Enum

from fastql.errors import GraphQLSyntaxError
from fastql.language.source import Source


class TokenKind(str, Enum):
    SOF = "<SOF>"
    EOF = "<EOF>"
    BANG = "!"
    DOLLAR = "$"
    AMP = "&"
    PAREN_L = "("
    PAREN_R = ")"
    SPREAD = "..."
    COLON = ":"
    EQUALS = "="
    AT = "@"
    BRACKET_L = "["
    BRACKET_R = "]"
    BRACE_L = "{"
    BRACE_R = "}"
    PIPE = "|"
    NAME = "Name"
    INT = "Int"
    FLOAT = "Float"
    STRING = "String"
    BLOCK_STRING = "BlockString"
    COMMENT = "Comment"


_PUNCT = {
    "!": TokenKind.BANG,
    "$": TokenKind.DOLLAR,
    "&": TokenKind.AMP,
    "(": TokenKind.PAREN_L,
    ")": TokenKind.PAREN_R,
    ":": TokenKind.COLON,
    "=": TokenKind.EQUALS,
    "@": TokenKind.AT,
    "[": TokenKind.BRACKET_L,
    "]": TokenKind.BRACKET_R,
    "{": TokenKind.BRACE_L,
    "}": TokenKind.BRACE_R,
    "|": TokenKind.PIPE,
}


class Token:
    """A single lexical token.

    ``value`` is set for name/number/string tokens (the decoded value for strings)
    and ``None`` for punctuators. ``start``/``end`` are character offsets.
    """

    __slots__ = ("kind", "start", "end", "value")

    def __init__(self, kind: TokenKind, start: int, end: int, value: str | None = None):
        self.kind = kind
        self.start = start
        self.end = end
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover - trivial
        desc = self.kind.value
        if self.value is not None:
            desc = f"{self.kind.value} {self.value!r}"
        return f"Token({desc} @ {self.start})"


def _is_name_start(ch: str) -> bool:
    return ch == "_" or "A" <= ch <= "Z" or "a" <= ch <= "z"


def _is_name_continue(ch: str) -> bool:
    return _is_name_start(ch) or "0" <= ch <= "9"


class Lexer:
    """Lazily tokenizes a :class:`Source`.

    The parser drives the lexer via :meth:`advance` (which returns the next
    significant token) and inspects :attr:`token` (the current token).
    """

    def __init__(self, source: Source | str):
        if isinstance(source, str):
            source = Source(source)
        self.source = source
        self.token = Token(TokenKind.SOF, 0, 0)

    def advance(self) -> Token:
        self.token = self._read_token(self.token.end)
        return self.token

    def lookahead(self) -> Token:
        """Return the next token without consuming the current one."""
        return self._read_token(self.token.end)

    # -- internals ------------------------------------------------------------

    def _syntax_error(self, position: int, description: str) -> GraphQLSyntaxError:
        return GraphQLSyntaxError(self.source, position, description)

    def _read_token(self, from_pos: int) -> Token:
        body = self.source.body
        n = len(body)
        pos = self._skip_ignored(from_pos)
        if pos >= n:
            return Token(TokenKind.EOF, pos, pos)

        ch = body[pos]

        # Spread "..."
        if ch == ".":
            if body[pos : pos + 3] == "...":
                return Token(TokenKind.SPREAD, pos, pos + 3)
            raise self._syntax_error(pos, f"Unexpected character {ch!r}.")

        # Single-char punctuators
        punct = _PUNCT.get(ch)
        if punct is not None:
            return Token(punct, pos, pos + 1)

        # Names
        if _is_name_start(ch):
            return self._read_name(pos)

        # Numbers
        if ch == "-" or "0" <= ch <= "9":
            return self._read_number(pos)

        # Strings
        if ch == '"':
            if body[pos : pos + 3] == '"""':
                return self._read_block_string(pos)
            return self._read_string(pos)

        raise self._syntax_error(pos, f"Cannot parse the unexpected character {ch!r}.")

    def _skip_ignored(self, pos: int) -> int:
        body = self.source.body
        n = len(body)
        while pos < n:
            ch = body[pos]
            if ch in " \t\r\n﻿" or ch == ",":
                pos += 1
            elif ch == "#":
                pos += 1
                while pos < n and body[pos] not in "\r\n":
                    pos += 1
            else:
                break
        return pos

    def _read_name(self, start: int) -> Token:
        body = self.source.body
        n = len(body)
        pos = start + 1
        while pos < n and _is_name_continue(body[pos]):
            pos += 1
        return Token(TokenKind.NAME, start, pos, body[start:pos])

    def _read_number(self, start: int) -> Token:
        body = self.source.body
        n = len(body)
        pos = start
        is_float = False

        if body[pos] == "-":
            pos += 1

        if pos < n and body[pos] == "0":
            pos += 1
            if pos < n and "0" <= body[pos] <= "9":
                raise self._syntax_error(
                    pos, f"Invalid number, unexpected digit after 0: {body[pos]!r}."
                )
        else:
            pos = self._read_digits(pos)

        # Fractional part
        if pos < n and body[pos] == ".":
            is_float = True
            pos += 1
            pos = self._read_digits(pos)

        # Exponent part
        if pos < n and body[pos] in "eE":
            is_float = True
            pos += 1
            if pos < n and body[pos] in "+-":
                pos += 1
            pos = self._read_digits(pos)

        kind = TokenKind.FLOAT if is_float else TokenKind.INT
        return Token(kind, start, pos, body[start:pos])

    def _read_digits(self, start: int) -> int:
        body = self.source.body
        n = len(body)
        if start >= n or not ("0" <= body[start] <= "9"):
            got = body[start] if start < n else "<EOF>"
            raise self._syntax_error(
                start, f"Invalid number, expected digit but got: {got!r}."
            )
        pos = start
        while pos < n and "0" <= body[pos] <= "9":
            pos += 1
        return pos

    def _read_string(self, start: int) -> Token:
        body = self.source.body
        n = len(body)
        pos = start + 1
        chunks: list[str] = []
        chunk_start = pos
        while pos < n:
            ch = body[pos]
            if ch == '"':
                chunks.append(body[chunk_start:pos])
                return Token(TokenKind.STRING, start, pos + 1, "".join(chunks))
            if ch in "\r\n":
                break
            if ch == "\\":
                chunks.append(body[chunk_start:pos])
                pos, decoded = self._read_escape(pos)
                chunks.append(decoded)
                chunk_start = pos
                continue
            pos += 1
        raise self._syntax_error(pos, "Unterminated string.")

    def _read_escape(self, pos: int) -> tuple[int, str]:
        body = self.source.body
        n = len(body)
        # body[pos] == "\\"
        if pos + 1 >= n:
            raise self._syntax_error(pos, "Unterminated string escape.")
        ch = body[pos + 1]
        simple = {
            '"': '"',
            "\\": "\\",
            "/": "/",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
        }
        if ch in simple:
            return pos + 2, simple[ch]
        if ch == "u":
            hex_digits = body[pos + 2 : pos + 6]
            if len(hex_digits) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex_digits):
                return pos + 6, chr(int(hex_digits, 16))
            raise self._syntax_error(
                pos, f"Invalid Unicode escape sequence: '\\u{hex_digits}'."
            )
        raise self._syntax_error(pos, f"Invalid character escape sequence: '\\{ch}'.")

    def _read_block_string(self, start: int) -> Token:
        body = self.source.body
        n = len(body)
        pos = start + 3
        raw_chunks: list[str] = []
        chunk_start = pos
        while pos < n:
            if body[pos : pos + 3] == '"""':
                raw_chunks.append(body[chunk_start:pos])
                raw_value = "".join(raw_chunks)
                value = dedent_block_string_value(raw_value)
                return Token(TokenKind.BLOCK_STRING, start, pos + 3, value)
            if body[pos] == "\\" and body[pos + 1 : pos + 4] == '"""':
                raw_chunks.append(body[chunk_start:pos])
                raw_chunks.append('"""')
                pos += 4
                chunk_start = pos
                continue
            pos += 1
        raise self._syntax_error(pos, "Unterminated block string.")


def dedent_block_string_value(raw: str) -> str:
    """Apply the GraphQL block-string formatting algorithm to ``raw``."""
    lines = raw.splitlines()

    common_indent = None
    for line in lines[1:]:
        stripped = line.lstrip(" \t")
        indent = len(line) - len(stripped)
        if stripped:  # line contains non-whitespace
            if common_indent is None or indent < common_indent:
                common_indent = indent

    if common_indent:
        lines = [lines[0]] + [line[common_indent:] for line in lines[1:]]

    # Remove leading and trailing blank lines.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)
