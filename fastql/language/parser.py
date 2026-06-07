"""A recursive-descent parser turning a token stream into a ``DocumentNode``.

Covers the executable subset of the GraphQL grammar: operations (including the
query shorthand), fragment definitions, selection sets, fields with aliases and
arguments, fragment spreads, inline fragments, variable definitions, directives,
all value literals, and type references. Unexpected tokens raise
:class:`~fastql.errors.GraphQLSyntaxError` with the offending source location.
"""

from __future__ import annotations

from fastql.errors import GraphQLSyntaxError
from fastql.language import ast
from fastql.language.lexer import Lexer, Token, TokenKind
from fastql.language.source import Source

_OPERATION_TYPES = {"query", "mutation", "subscription"}


def parse(source: Source | str) -> ast.DocumentNode:
    """Parse a GraphQL document and return its AST."""
    return Parser(source).parse_document()


class Parser:
    def __init__(self, source: Source | str):
        if isinstance(source, str):
            source = Source(source)
        self.source = source
        self.lexer = Lexer(source)
        self._last_token = self.lexer.token  # the SOF sentinel
        self.lexer.advance()  # load the first significant token

    # -- entry point ----------------------------------------------------------

    def parse_document(self) -> ast.DocumentNode:
        start = self.lexer.token
        definitions = [self.parse_definition()]
        while not self._peek(TokenKind.EOF):
            definitions.append(self.parse_definition())
        return ast.DocumentNode(definitions, self._loc(start))

    def parse_definition(self) -> ast.DefinitionNode:
        token = self.lexer.token
        if token.kind == TokenKind.BRACE_L:
            return self.parse_operation_definition()
        if token.kind == TokenKind.NAME:
            if token.value in _OPERATION_TYPES:
                return self.parse_operation_definition()
            if token.value == "fragment":
                return self.parse_fragment_definition()
        raise self._unexpected(token)

    # -- operations -----------------------------------------------------------

    def parse_operation_definition(self) -> ast.OperationDefinitionNode:
        start = self.lexer.token
        if start.kind == TokenKind.BRACE_L:
            # Query shorthand: a bare selection set.
            selection_set = self.parse_selection_set()
            return ast.OperationDefinitionNode(
                operation="query", selection_set=selection_set, loc=self._loc(start)
            )
        operation = self._parse_operation_type()
        name = self.parse_name() if self._peek(TokenKind.NAME) else None
        variable_definitions = self.parse_variable_definitions()
        directives = self.parse_directives(is_const=False)
        selection_set = self.parse_selection_set()
        return ast.OperationDefinitionNode(
            operation=operation,
            selection_set=selection_set,
            name=name,
            variable_definitions=variable_definitions,
            directives=directives,
            loc=self._loc(start),
        )

    def _parse_operation_type(self) -> str:
        token = self._expect_token(TokenKind.NAME)
        if token.value in _OPERATION_TYPES:
            return token.value
        raise self._unexpected(token)

    def parse_variable_definitions(self) -> list[ast.VariableDefinitionNode]:
        if self._peek(TokenKind.PAREN_L):
            return self._many(
                TokenKind.PAREN_L, self.parse_variable_definition, TokenKind.PAREN_R
            )
        return []

    def parse_variable_definition(self) -> ast.VariableDefinitionNode:
        start = self.lexer.token
        variable = self.parse_variable()
        self._expect_token(TokenKind.COLON)
        type_ref = self.parse_type_reference()
        default_value = None
        if self._expect_optional_token(TokenKind.EQUALS):
            default_value = self.parse_value_literal(is_const=True)
        directives = self.parse_directives(is_const=True)
        return ast.VariableDefinitionNode(
            variable=variable,
            type=type_ref,
            default_value=default_value,
            directives=directives,
            loc=self._loc(start),
        )

    def parse_variable(self) -> ast.VariableNode:
        start = self.lexer.token
        self._expect_token(TokenKind.DOLLAR)
        name = self.parse_name()
        return ast.VariableNode(name=name, loc=self._loc(start))

    # -- selections -----------------------------------------------------------

    def parse_selection_set(self) -> ast.SelectionSetNode:
        start = self.lexer.token
        selections = self._many(
            TokenKind.BRACE_L, self.parse_selection, TokenKind.BRACE_R
        )
        return ast.SelectionSetNode(selections=selections, loc=self._loc(start))

    def parse_selection(self) -> ast.SelectionNode:
        if self._peek(TokenKind.SPREAD):
            return self.parse_fragment()
        return self.parse_field()

    def parse_field(self) -> ast.FieldNode:
        start = self.lexer.token
        name_or_alias = self.parse_name()
        if self._expect_optional_token(TokenKind.COLON):
            alias: ast.NameNode | None = name_or_alias
            name = self.parse_name()
        else:
            alias = None
            name = name_or_alias
        arguments = self.parse_arguments(is_const=False)
        directives = self.parse_directives(is_const=False)
        selection_set = None
        if self._peek(TokenKind.BRACE_L):
            selection_set = self.parse_selection_set()
        return ast.FieldNode(
            name=name,
            alias=alias,
            arguments=arguments,
            directives=directives,
            selection_set=selection_set,
            loc=self._loc(start),
        )

    def parse_fragment(self) -> ast.SelectionNode:
        start = self.lexer.token
        self._expect_token(TokenKind.SPREAD)
        has_type_condition = self._expect_optional_keyword("on")
        if not has_type_condition and self._peek(TokenKind.NAME):
            name = self.parse_fragment_name()
            directives = self.parse_directives(is_const=False)
            return ast.FragmentSpreadNode(
                name=name, directives=directives, loc=self._loc(start)
            )
        type_condition = self.parse_named_type() if has_type_condition else None
        directives = self.parse_directives(is_const=False)
        selection_set = self.parse_selection_set()
        return ast.InlineFragmentNode(
            selection_set=selection_set,
            type_condition=type_condition,
            directives=directives,
            loc=self._loc(start),
        )

    def parse_fragment_definition(self) -> ast.FragmentDefinitionNode:
        start = self.lexer.token
        self._expect_keyword("fragment")
        name = self.parse_fragment_name()
        self._expect_keyword("on")
        type_condition = self.parse_named_type()
        directives = self.parse_directives(is_const=False)
        selection_set = self.parse_selection_set()
        return ast.FragmentDefinitionNode(
            name=name,
            type_condition=type_condition,
            selection_set=selection_set,
            directives=directives,
            loc=self._loc(start),
        )

    def parse_fragment_name(self) -> ast.NameNode:
        if self.lexer.token.value == "on":
            raise self._unexpected(self.lexer.token)
        return self.parse_name()

    # -- arguments & directives ----------------------------------------------

    def parse_arguments(self, is_const: bool) -> list[ast.ArgumentNode]:
        if self._peek(TokenKind.PAREN_L):
            return self._many(
                TokenKind.PAREN_L,
                lambda: self.parse_argument(is_const),
                TokenKind.PAREN_R,
            )
        return []

    def parse_argument(self, is_const: bool) -> ast.ArgumentNode:
        start = self.lexer.token
        name = self.parse_name()
        self._expect_token(TokenKind.COLON)
        value = self.parse_value_literal(is_const)
        return ast.ArgumentNode(name=name, value=value, loc=self._loc(start))

    def parse_directives(self, is_const: bool) -> list[ast.DirectiveNode]:
        directives: list[ast.DirectiveNode] = []
        while self._peek(TokenKind.AT):
            directives.append(self.parse_directive(is_const))
        return directives

    def parse_directive(self, is_const: bool) -> ast.DirectiveNode:
        start = self.lexer.token
        self._expect_token(TokenKind.AT)
        name = self.parse_name()
        arguments = self.parse_arguments(is_const)
        return ast.DirectiveNode(name=name, arguments=arguments, loc=self._loc(start))

    # -- values ---------------------------------------------------------------

    def parse_value_literal(self, is_const: bool) -> ast.ValueNode:
        token = self.lexer.token
        kind = token.kind
        if kind == TokenKind.BRACKET_L:
            return self.parse_list(is_const)
        if kind == TokenKind.BRACE_L:
            return self.parse_object(is_const)
        if kind == TokenKind.INT:
            self._advance_lexer()
            return ast.IntValueNode(value=token.value, loc=self._loc(token))
        if kind == TokenKind.FLOAT:
            self._advance_lexer()
            return ast.FloatValueNode(value=token.value, loc=self._loc(token))
        if kind in (TokenKind.STRING, TokenKind.BLOCK_STRING):
            self._advance_lexer()
            return ast.StringValueNode(
                value=token.value,
                block=kind == TokenKind.BLOCK_STRING,
                loc=self._loc(token),
            )
        if kind == TokenKind.NAME:
            self._advance_lexer()
            if token.value == "true":
                return ast.BooleanValueNode(value=True, loc=self._loc(token))
            if token.value == "false":
                return ast.BooleanValueNode(value=False, loc=self._loc(token))
            if token.value == "null":
                return ast.NullValueNode(loc=self._loc(token))
            return ast.EnumValueNode(value=token.value, loc=self._loc(token))
        if kind == TokenKind.DOLLAR and not is_const:
            return self.parse_variable()
        raise self._unexpected(token)

    def parse_list(self, is_const: bool) -> ast.ListValueNode:
        start = self.lexer.token
        values = self._any(
            TokenKind.BRACKET_L,
            lambda: self.parse_value_literal(is_const),
            TokenKind.BRACKET_R,
        )
        return ast.ListValueNode(values=values, loc=self._loc(start))

    def parse_object(self, is_const: bool) -> ast.ObjectValueNode:
        start = self.lexer.token
        fields = self._any(
            TokenKind.BRACE_L,
            lambda: self.parse_object_field(is_const),
            TokenKind.BRACE_R,
        )
        return ast.ObjectValueNode(fields=fields, loc=self._loc(start))

    def parse_object_field(self, is_const: bool) -> ast.ObjectFieldNode:
        start = self.lexer.token
        name = self.parse_name()
        self._expect_token(TokenKind.COLON)
        value = self.parse_value_literal(is_const)
        return ast.ObjectFieldNode(name=name, value=value, loc=self._loc(start))

    # -- type references ------------------------------------------------------

    def parse_type_reference(self) -> ast.TypeNode:
        start = self.lexer.token
        if self._expect_optional_token(TokenKind.BRACKET_L):
            inner = self.parse_type_reference()
            self._expect_token(TokenKind.BRACKET_R)
            type_ref: ast.TypeNode = ast.ListTypeNode(type=inner, loc=self._loc(start))
        else:
            type_ref = self.parse_named_type()
        if self._expect_optional_token(TokenKind.BANG):
            return ast.NonNullTypeNode(type=type_ref, loc=self._loc(start))
        return type_ref

    def parse_named_type(self) -> ast.NamedTypeNode:
        start = self.lexer.token
        name = self.parse_name()
        return ast.NamedTypeNode(name=name, loc=self._loc(start))

    # -- primitives -----------------------------------------------------------

    def parse_name(self) -> ast.NameNode:
        token = self._expect_token(TokenKind.NAME)
        return ast.NameNode(value=token.value, loc=self._loc(token))

    # -- token helpers --------------------------------------------------------

    def _peek(self, kind: TokenKind) -> bool:
        return self.lexer.token.kind == kind

    def _advance_lexer(self) -> None:
        self._last_token = self.lexer.token
        self.lexer.advance()

    def _expect_token(self, kind: TokenKind) -> Token:
        token = self.lexer.token
        if token.kind == kind:
            self._advance_lexer()
            return token
        raise self._syntax_error(
            token.start,
            f"Expected {self._kind_desc(kind)}, found {self._token_desc(token)}.",
        )

    def _expect_optional_token(self, kind: TokenKind) -> bool:
        if self.lexer.token.kind == kind:
            self._advance_lexer()
            return True
        return False

    def _expect_keyword(self, value: str) -> None:
        token = self.lexer.token
        if token.kind == TokenKind.NAME and token.value == value:
            self._advance_lexer()
            return
        raise self._syntax_error(
            token.start, f'Expected "{value}", found {self._token_desc(token)}.'
        )

    def _expect_optional_keyword(self, value: str) -> bool:
        token = self.lexer.token
        if token.kind == TokenKind.NAME and token.value == value:
            self._advance_lexer()
            return True
        return False

    def _loc(self, start_token: Token) -> ast.Location:
        return ast.Location(start_token.start, self._last_token.end, self.source)

    def _unexpected(self, token: Token) -> GraphQLSyntaxError:
        return self._syntax_error(
            token.start, f"Unexpected {self._token_desc(token)}."
        )

    def _syntax_error(self, position: int, description: str) -> GraphQLSyntaxError:
        return GraphQLSyntaxError(self.source, position, description)

    @staticmethod
    def _kind_desc(kind: TokenKind) -> str:
        if kind in (TokenKind.NAME, TokenKind.INT, TokenKind.FLOAT, TokenKind.STRING):
            return kind.value
        return f'"{kind.value}"'

    @staticmethod
    def _token_desc(token: Token) -> str:
        if token.kind == TokenKind.EOF:
            return "<EOF>"
        if token.kind == TokenKind.NAME:
            return f'Name "{token.value}"'
        if token.value is not None and token.kind in (
            TokenKind.INT,
            TokenKind.FLOAT,
            TokenKind.STRING,
            TokenKind.BLOCK_STRING,
        ):
            return f"{token.kind.value} {token.value!r}"
        return f'"{token.kind.value}"'

    def _many(self, open_kind, parse_fn, close_kind) -> list:
        self._expect_token(open_kind)
        nodes = [parse_fn()]
        while not self._expect_optional_token(close_kind):
            nodes.append(parse_fn())
        return nodes

    def _any(self, open_kind, parse_fn, close_kind) -> list:
        self._expect_token(open_kind)
        nodes: list = []
        while not self._expect_optional_token(close_kind):
            nodes.append(parse_fn())
        return nodes
