## Why

FastQL's custom parser is fast and dependency-free, but its current test surface is too small to provide reference-level confidence in Unicode handling, malformed input, source locations, diagnostics, and future GraphQL language changes. Hardening it against the GraphQL September 2025 executable-document grammar preserves FastQL's runtime advantages while making correctness measurable against upstream conformance suites and a pinned development oracle.

## What Changes

- Declare GraphQL September 2025 executable documents as the parser's fixed supported language target; schema definition language (SDL) remains unsupported.
- Correct lexical and parsing behavior for Unicode escapes and surrogate pairs, control characters, number boundaries, strings and block strings, ignored tokens, source locations, and syntax diagnostics.
- Support September 2025 descriptions on operation, fragment, and variable definitions through additive fields on the existing AST classes and deterministic printer output.
- Add optional `SchemaConfig.max_query_tokens` and `SchemaConfig.max_query_depth` controls, unlimited by default, and report configured-limit or recursion-risk failures as `GraphQLSyntaxError` values.
- Import and version the applicable GraphQL.js lexer/parser test corpus with upstream provenance, licensing, and an intentional exclusion list for SDL and experimental cases.
- Pin `graphql-core==3.2.11` as a development-only differential-testing oracle, comparing acceptance, rejection, decoded values, AST structure, source locations, and error positions.
- Add deterministic property tests, malformed-input generation, scheduled fuzz testing, minimized regression fixtures, and GraphQL.js parser-release monitoring.
- Establish reproducible parser benchmarks that require FastQL to outperform the pinned oracle on small, medium, and large executable documents and by at least 1.5x in aggregate.
- Preserve the existing FastQL lexer/parser/AST public imports, syntax-error serialization, printer contract, and zero-runtime-dependency packaging.

### Non-goals / Out of Scope

- SDL parsing, schema construction through GraphQL source text, experimental GraphQL features, and exact GraphQL-core error-message wording are out of scope.
- This change does not adopt GraphQL-core, GraphQL.js, a parser generator, or a fuzzing library as a runtime dependency.
- This change does not replace FastQL validation or execution with GraphQL-core and does not add transport-specific parser implementations.
- Automatically adopting future GraphQL specification or GraphQL.js releases is out of scope; each upgrade requires explicit review.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `language-parsing`: Define the supported specification and executable-document scope, strengthen lexical and syntax conformance, add configurable token/depth limits, and require conformance, differential, fuzz, and performance verification.
- `integration-packaging`: Require GraphQL-core and upstream conformance tooling to remain development-only and absent from runtime distribution metadata.

## Impact

- The language lexer, parser, source-location handling, syntax diagnostics, parser configuration flow, execution/subscription entry points, and shared HTTP/WebSocket query inspection will change.
- `SchemaConfig` gains `max_query_tokens` and `max_query_depth`; both default to `None` for compatibility.
- Development dependencies, CI workflows, conformance fixtures, benchmark tooling, parser documentation, and release maintenance procedures expand.
- Stricter conformance can reject malformed documents previously accepted; valid existing executable documents remain supported, while operation, fragment, and variable-definition AST nodes gain optional additive `description` fields.
- Runtime installations remain dependency-free and continue to avoid importing GraphQL-core or web-framework packages.
