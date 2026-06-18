## MODIFIED Requirements

### Requirement: Tokenize a GraphQL document

The lexer SHALL tokenize executable documents according to the lexical grammar of the GraphQL September 2025 specification. It SHALL produce names, integer and float literals, decoded single-line and block string literals, and GraphQL punctuators; ignore commas, supported whitespace, byte-order marks, and comments; preserve character offsets; and reject invalid Unicode escapes, isolated surrogates, prohibited control characters, malformed numbers, invalid token adjacency, and unexpected characters at the offending position.

#### Scenario: Lexing a simple selection

- **WHEN** the lexer is given `{ user(id: 1) { name } }`
- **THEN** it produces tokens for `{`, `user`, `(`, `id`, `:`, `1`, `)`, `{`, `name`, `}`, `}` followed by an end-of-file token with accurate source spans

#### Scenario: Block string literal

- **WHEN** the lexer is given a triple-quoted block string containing indentation and an escaped triple quote
- **THEN** it produces one block-string token with the September 2025 value and indentation algorithms applied

#### Scenario: Unicode escape forms

- **WHEN** a string contains a valid fixed-width escape, surrogate pair, or variable-width escape such as `\u{1F4A9}`
- **THEN** the lexer emits the decoded Unicode scalar value

#### Scenario: Invalid string character

- **WHEN** a string contains an isolated surrogate escape or a prohibited unescaped control character
- **THEN** the lexer raises `GraphQLSyntaxError` at the invalid escape or character

#### Scenario: Invalid number boundary

- **WHEN** a number contains a leading zero, incomplete fraction or exponent, or invalid adjacent name character
- **THEN** the lexer raises `GraphQLSyntaxError` at the first character that makes the number invalid

#### Scenario: Invalid character

- **WHEN** the lexer encounters a character that cannot begin any token
- **THEN** it raises `GraphQLSyntaxError` carrying the line and column of that character

### Requirement: Parse a document into an AST

The parser SHALL consume the token stream and produce the existing FastQL located AST for executable documents defined by the GraphQL September 2025 specification, including described operation, fragment, and variable definitions; selection sets; fields; arguments; fragment spreads; inline fragments; directives; values; and type references. Existing definition node classes SHALL expose optional additive description fields, and the printer SHALL preserve descriptions while leaving undescribed output unchanged. The parser SHALL reject SDL and unsupported experimental definitions, preserve existing public AST/import contracts, and convert malformed or unsafe recursive input into `GraphQLSyntaxError` rather than leaking implementation exceptions.

#### Scenario: Named query with variables

- **WHEN** the parser is given `query GetUser($id: ID!) { user(id: $id) { name } }`
- **THEN** it produces a located `DocumentNode` with one query operation named `GetUser`, one non-null `ID` variable definition, and the expected `user` selection

#### Scenario: Fragments

- **WHEN** the parser is given a query using a fragment spread and an inline fragment
- **THEN** the resulting AST contains located `FragmentSpreadNode` and `InlineFragmentNode` values

#### Scenario: Described executable definitions

- **WHEN** an operation, fragment definition, or variable definition has a September 2025 string description
- **THEN** the corresponding existing AST node carries a located `StringValueNode` description and printing then reparsing preserves it

#### Scenario: Query shorthand description rejected

- **WHEN** a description is followed directly by a shorthand selection set
- **THEN** the parser raises a located `GraphQLSyntaxError` because descriptions are not allowed on query shorthand

#### Scenario: Syntax error reporting

- **WHEN** the parser encounters an unexpected token or end of input
- **THEN** it raises `GraphQLSyntaxError` with a human-readable category and the source position of the unexpected input

#### Scenario: SDL remains unsupported

- **WHEN** the parser receives a type-system definition such as `type Query { name: String }`
- **THEN** it rejects the document as unsupported executable syntax

#### Scenario: Recursive input safety

- **WHEN** input nesting approaches or exceeds the parser's safe recursion capacity
- **THEN** parsing returns a located `GraphQLSyntaxError` and does not expose `RecursionError`

## ADDED Requirements

### Requirement: Declare a fixed language compatibility target

FastQL SHALL identify GraphQL September 2025 executable documents as the supported parser contract. Documentation and conformance metadata SHALL distinguish this target from SDL, experimental grammar, and future GraphQL specification releases.

#### Scenario: Compatibility target is inspectable

- **WHEN** a maintainer or user inspects parser documentation and conformance metadata
- **THEN** the GraphQL September 2025 version and executable-document-only scope are stated consistently

#### Scenario: Future specification release

- **WHEN** a newer GraphQL specification or GraphQL.js parser release becomes available
- **THEN** FastQL retains its declared target until a reviewed change updates the contract and conformance corpus

### Requirement: Enforce configurable parser resource limits

FastQL SHALL expose `SchemaConfig.max_query_tokens` and `SchemaConfig.max_query_depth` as positive integers or `None`, defaulting to `None`. Token limits SHALL count significant GraphQL tokens while excluding ignored input and sentinels. Depth limits SHALL count syntactic selection, value-container, and list-type nesting. Direct parser calls SHALL accept equivalent keyword-only limits, and all FastQL entry points that parse a query string SHALL apply the owning schema's configured limits.

#### Scenario: Unlimited defaults preserve compatibility

- **WHEN** both parser limits are `None`
- **THEN** no user-configured token or syntactic-depth policy rejects an otherwise valid document

#### Scenario: Token limit exceeded

- **WHEN** a query contains more significant tokens than `max_query_tokens`
- **THEN** direct parsing and execution-facing parsing fail with a located `GraphQLSyntaxError` before validation or execution

#### Scenario: Depth limit exceeded

- **WHEN** a query's syntactic container nesting exceeds `max_query_depth`
- **THEN** direct parsing and execution-facing parsing fail with a located `GraphQLSyntaxError` at the opening token that exceeds the limit

#### Scenario: Invalid parser limit configuration

- **WHEN** either configured limit is zero, negative, boolean, or not an integer
- **THEN** schema or parser construction rejects the configuration with an actionable `ValueError`

#### Scenario: Pre-parsed document

- **WHEN** execution receives an existing `DocumentNode` instead of a source string
- **THEN** parser token and depth limits are not reapplied

### Requirement: Verify reference-level language conformance

FastQL SHALL maintain a versioned, attributed import of applicable GraphQL.js 16.14.1 lexer/parser cases and SHALL differentially test FastQL against `graphql-core==3.2.11` as a development-only oracle. Tests SHALL compare acceptance, rejection category and position, decoded token values, normalized AST structure, node locations, and parse-print-parse structure. Every excluded or intentionally divergent case SHALL be classified with a reviewed rationale.

#### Scenario: Applicable upstream case

- **WHEN** an imported GraphQL.js case covers September 2025 executable syntax
- **THEN** FastQL passes the case and the differential harness reports no unexplained mismatch

#### Scenario: Unsupported upstream case

- **WHEN** an imported case covers SDL, experimental grammar, or a documented oracle/specification difference
- **THEN** the fixture manifest records its exact category and rationale rather than silently skipping it

#### Scenario: Differential mismatch discovered

- **WHEN** FastQL and the pinned oracle differ on acceptance, decoded value, normalized AST, location, or rejection position
- **THEN** CI fails unless the exact case is present in the reviewed intentional-difference allowlist

#### Scenario: Fuzz failure becomes regression coverage

- **WHEN** property or fuzz testing finds a new parser defect or unexplained oracle mismatch
- **THEN** the minimized input is committed as a deterministic regression case before the defect is considered fixed

### Requirement: Preserve the parser performance advantage

FastQL SHALL provide a reproducible benchmark comparing location-enabled FastQL and GraphQL-core parsing on the same Python interpreter using fixed small, medium, and large executable documents. Median warmed timings SHALL show FastQL faster for every workload and at least 1.5 times faster in aggregate.

#### Scenario: Parser performance gate passes

- **WHEN** the benchmark runs on a supported Python version in the dedicated CI environment
- **THEN** FastQL is faster on each fixture and the sum of oracle medians divided by the sum of FastQL medians is at least `1.5`

#### Scenario: Parser performance regression

- **WHEN** any workload is slower than the oracle or the aggregate ratio falls below `1.5`
- **THEN** the benchmark job fails and reports per-workload medians and ratios

### Requirement: Track upstream parser releases

FastQL SHALL run a scheduled check comparing the pinned GraphQL.js and GraphQL-core versions with their latest stable releases. A newly available release SHALL require an explicit recorded decision to upgrade through a reviewed change or defer until a stated review date.

#### Scenario: New upstream release detected

- **WHEN** the scheduled check finds a stable GraphQL.js or GraphQL-core version newer than the conformance manifest
- **THEN** it opens or updates a maintenance issue with release links and reports the pin as awaiting review

#### Scenario: Upstream pin remains current or reviewed

- **WHEN** no newer stable release exists or a deferral decision remains valid
- **THEN** the monitoring check succeeds without modifying parser code, fixtures, or dependencies
