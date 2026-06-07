# language-parsing Specification

## Purpose
Lexing and parsing GraphQL documents into a located AST.
## Requirements
### Requirement: Tokenize a GraphQL document

The lexer SHALL convert a GraphQL source string into a stream of tokens covering names, integer and
float literals, single-line and block string literals, and all GraphQL punctuators
(`! $ & ( ) ... : = @ [ ] { | }`). The lexer SHALL ignore insignificant commas, whitespace, and
comments per the GraphQL specification.

#### Scenario: Lexing a simple selection

- **WHEN** the lexer is given `{ user(id: 1) { name } }`
- **THEN** it produces tokens for `{`, `user`, `(`, `id`, `:`, `1`, `)`, `{`, `name`, `}`, `}` followed by an end-of-file token

#### Scenario: Block string literal

- **WHEN** the lexer is given a triple-quoted block string
- **THEN** it produces a single string token with the block-string indentation rules applied

#### Scenario: Invalid character

- **WHEN** the lexer encounters a character that cannot begin any token
- **THEN** it raises a syntax error carrying the line and column of the offending character

### Requirement: Parse a document into an AST

The parser SHALL consume the token stream and produce a `Document` AST containing operation
definitions (query/mutation/subscription), fragment definitions, selection sets, fields, arguments,
fragment spreads, inline fragments, variable definitions, directives, and value/type-reference nodes.
Every AST node SHALL retain its source location.

#### Scenario: Named query with variables

- **WHEN** the parser is given `query GetUser($id: ID!) { user(id: $id) { name } }`
- **THEN** it produces a `Document` with one operation of type `query` named `GetUser`, one variable definition `$id` of non-null type `ID`, and a selection set containing the `user` field

#### Scenario: Fragments

- **WHEN** the parser is given a query using a fragment spread and an inline fragment
- **THEN** the resulting AST contains a `FragmentSpread` node and an `InlineFragment` node in the selection set

#### Scenario: Syntax error reporting

- **WHEN** the parser encounters an unexpected token (for example a missing closing brace)
- **THEN** it raises a syntax error containing a human-readable message and the source location of the unexpected token

