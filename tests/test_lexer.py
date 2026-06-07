"""Lexer tests covering the language-parsing 'Tokenize a GraphQL document' scenarios."""

import pytest

from fastql.errors import GraphQLSyntaxError
from fastql.language.lexer import Lexer, TokenKind


def tokenize(text):
    lexer = Lexer(text)
    tokens = []
    while True:
        tok = lexer.advance()
        if tok.kind == TokenKind.EOF:
            tokens.append(tok)
            break
        tokens.append(tok)
    return tokens


def test_lexing_a_simple_selection():
    tokens = tokenize("{ user(id: 1) { name } }")
    kinds = [(t.kind, t.value) for t in tokens]
    assert kinds == [
        (TokenKind.BRACE_L, None),
        (TokenKind.NAME, "user"),
        (TokenKind.PAREN_L, None),
        (TokenKind.NAME, "id"),
        (TokenKind.COLON, None),
        (TokenKind.INT, "1"),
        (TokenKind.PAREN_R, None),
        (TokenKind.BRACE_L, None),
        (TokenKind.NAME, "name"),
        (TokenKind.BRACE_R, None),
        (TokenKind.BRACE_R, None),
        (TokenKind.EOF, None),
    ]


def test_ignores_commas_whitespace_and_comments():
    tokens = tokenize("{\n  a, # a comment\n  b\n}")
    names = [t.value for t in tokens if t.kind == TokenKind.NAME]
    assert names == ["a", "b"]


def test_block_string_produces_single_token_with_indentation_applied():
    source = '"""\n    Hello\n      World\n    """'
    tokens = tokenize(source)
    assert len(tokens) == 2  # block string + EOF
    assert tokens[0].kind == TokenKind.BLOCK_STRING
    assert tokens[0].value == "Hello\n  World"


def test_simple_string_with_escapes():
    tokens = tokenize(r'"line\nbreak \"q\""')
    assert tokens[0].kind == TokenKind.STRING
    assert tokens[0].value == 'line\nbreak "q"'


def test_float_vs_int():
    assert tokenize("3")[0].kind == TokenKind.INT
    assert tokenize("3.14")[0].kind == TokenKind.FLOAT
    assert tokenize("1e10")[0].kind == TokenKind.FLOAT
    assert tokenize("-0.5e-2")[0].kind == TokenKind.FLOAT


def test_invalid_character_reports_line_and_column():
    with pytest.raises(GraphQLSyntaxError) as exc:
        tokenize("{ a\n  % }")
    err = exc.value
    assert err.locations
    loc = err.locations[0]
    assert (loc.line, loc.column) == (2, 3)
