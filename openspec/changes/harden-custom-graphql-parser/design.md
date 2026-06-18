## Context

FastQL currently implements a lazy lexer and recursive-descent parser for executable GraphQL documents. The implementation is compact and benchmarks about twice as fast as GraphQL-core on representative documents, but focused coverage is limited and known gaps include variable-width Unicode escapes, surrogate validation, control-character rejection, diagnostic precision, and uncontrolled recursion at deeply nested input.

The language layer is public: callers can import `Source`, `Lexer`, `Token`, `TokenKind`, AST dataclasses, `Parser`, `parse`, and `print_ast`. Validation, execution, subscriptions, HTTP request inspection, WebSocket handling, scalar coercion, uploads, and federation field-set parsing all consume these types. The change must therefore improve conformance without replacing the AST or introducing a runtime dependency.

GraphQL-core 3.2.11 is aligned with GraphQL.js 16.14.1 and provides a practical Python oracle for the selected upstream language corpus. GraphQL September 2025 is the normative language target; differences between that specification and the pinned oracle must be explicit rather than silently inherited.

## Goals / Non-Goals

**Goals:**

- Make FastQL conform to the GraphQL September 2025 executable-document lexical and syntactic grammar.
- Preserve the existing language API, AST representation, error serialization, printer behavior, and dependency-free runtime package.
- Establish reproducible conformance, differential, property, fuzz, regression, and performance verification.
- Add parser resource controls that are consistently honored by every string-query entry point.
- Prevent malformed or deeply nested input from leaking raw `RecursionError` or implementation exceptions.
- Detect upstream GraphQL.js parser releases so support changes are reviewed intentionally.

**Non-Goals:**

- Parsing SDL/type-system documents or adopting experimental GraphQL grammar.
- Matching GraphQL-core's exact English error wording or replacing FastQL validation/execution.
- Automatically updating the supported specification, oracle, or imported corpus.
- Adding GraphQL-core, GraphQL.js, Hypothesis, or benchmark tooling to runtime dependencies.
- Defining semantic query-cost or resolver-complexity limits; the depth control is syntactic parser protection.

## Decisions

### Fix the language contract at GraphQL September 2025 executable documents

The parser will publish a single specification identifier for diagnostics, documentation, and test manifests. It accepts executable definitions and value/type syntax needed by operations, while rejecting SDL definitions even when the pinned oracle can parse them.

This is preferred over claiming generic "GraphQL" compatibility because correctness can only be measured against a fixed grammar. Following GraphQL-core implicitly is rejected because its release cadence and supported draft features do not define FastQL's public contract.

### Preserve the FastQL frontend and harden it in place

The current lexer, parser, AST dataclasses, source types, and printer remain canonical. Lexical behavior will be corrected in the lexer and parser productions will be aligned with the selected grammar. Existing public import paths and positional constructor behavior remain stable; `OperationDefinitionNode`, `FragmentDefinitionNode`, and `VariableDefinitionNode` gain optional `description: StringValueNode | None` fields appended after existing fields so old calls remain valid. The printer emits descriptions before the described definition and leaves output unchanged for nodes without descriptions. Query shorthand remains undescribed as required by the grammar.

Replacing the parser with GraphQL-core was rejected because measured parsing was approximately 1.9-2.4 times slower before any AST conversion, would end the zero-runtime-dependency guarantee, and would introduce breaking AST semantics. A parser generator was rejected because the existing grammar is small and most remaining risk lies in lexical edge cases, diagnostics, and conformance maintenance rather than production count.

### Use a versioned, generated upstream conformance corpus

Committed fixtures under `tests/conformance/graphql_js/` will include a machine-readable manifest containing GraphQL.js version `16.14.1`, source commit, source URLs, import timestamp, selected upstream test files, fixture checksums, license reference, and categorized exclusions. A manual update script will fetch only a requested immutable tag/commit, verify provenance, translate applicable lexer/parser cases into stable JSON fixtures, and refuse uncommitted or unclassified cases.

Generated fixtures, the upstream MIT license notice, and the translation script are committed so normal tests require no network. Cases are classified as applicable executable grammar, SDL, experimental, harness-only, or intentionally divergent. Exclusions require a reason and review; broad filename-level skipping is not allowed when individual executable cases can be imported.

Directly copying upstream TypeScript tests was rejected because it would require Node.js and GraphQL.js in routine Python CI. Hand-maintaining selected examples was rejected because it would drift and lose provenance.

### Use GraphQL-core as a pinned differential oracle

`graphql-core==3.2.11`, corresponding to GraphQL.js 16.14.1, will be added only to the development dependency group. A differential harness will run the same corpus and generated inputs through FastQL and GraphQL-core and normalize outcomes:

- accepted documents: decoded token values, a structural AST projection, node spans, and printed/reparsed structure;
- rejected documents: rejection category and absolute source position, with line/column derived from the source;
- unsupported or specification-intentional differences: exact fixture ID and rationale in a reviewed allowlist.

The AST projection will serialize node kinds and semantic fields while normalizing FastQL lists versus oracle tuples and operation strings versus enums. It will exclude Python class identity and source-object identity. Error wording is not compared, but a mismatch in acceptance, error category, or position is a failure unless allowlisted.

Using GraphQL-core at runtime as fallback is rejected because it would hide parser defects, produce environment-dependent behavior, and violate packaging constraints.

### Correct lexical behavior before expanding parser productions

The lexer will implement September 2025 string semantics, including fixed-width and variable-width Unicode escapes, surrogate-pair composition, rejection of isolated surrogates and prohibited control characters, and exact block-string escaped-triple-quote and indentation behavior. Number scanning will enforce leading-zero, fraction, exponent, and name-adjacency boundaries at the offending character. Ignored BOM, whitespace, commas, comments, CR/LF handling, and source offsets will be covered independently from parser tests.

Lexical decoding remains explicit code rather than relying on Python's JSON or Unicode escape codecs because GraphQL escape validity and source-position reporting differ from those generic codecs.

### Add token and syntactic-depth controls to parser configuration

`SchemaConfig` gains `max_query_tokens: int | None = None` and `max_query_depth: int | None = None`. Values must be positive integers or `None`; `None` means no user-configured policy limit. Direct callers gain equivalent keyword-only arguments on `parse` and `Parser`, with explicit arguments taking precedence over defaults passed by execution.

Token count includes significant GraphQL tokens and punctuators but excludes SOF/EOF, whitespace, commas, BOMs, and comments. The lexer increments the count as significant tokens are produced and raises `GraphQLSyntaxError` before returning a token beyond the configured maximum.

Depth is syntactic container depth, not schema-aware query complexity. The root selection set has depth 1; nested selection sets, list/object values, and nested list type references increment the active grammar-container depth. The parser enters and exits depth through one guard used by every recursive production. A configured excess raises `GraphQLSyntaxError` at the opening token.

When no depth limit is configured, the parser still uses an internal interpreter-safety guard so raw `RecursionError` never escapes. This guard is an implementation safety ceiling, not a documented query policy. The public error description distinguishes configured depth rejection from parser safety rejection.

Every path that parses a string will pass the owning schema's limits: `execute`, incremental execution, `subscribe`, shared HTTP operation classification and incremental scanning, WebSocket subscription setup, testing clients, and federation field-set parsing where a schema configuration is available. Pre-parsed `DocumentNode` inputs bypass parser limits by design.

### Use deterministic properties and bounded fuzz campaigns

Hypothesis will be a development dependency. Deterministic property tests with fixed settings and persisted examples will generate valid names, numbers, strings, block strings, Unicode escapes, comments, values, directives, fragments, operations, and nested containers. Mutation strategies will produce truncation, delimiter imbalance, invalid escapes, numeric suffixes, prohibited controls, invalid adjacency, and malformed spread/fragment constructs.

Minimized failures become committed regression fixtures before a fix is considered complete. Pull-request CI runs deterministic bounded examples with a fixed seed/profile; a scheduled and manually dispatched extended job runs larger example counts and stores failing inputs as artifacts. Random fuzzing without reproducible seeds or minimized cases is rejected because it produces unactionable intermittent failures.

### Treat performance as a relative compatibility gate

A standalone benchmark command will parse fixed small, medium, and large executable documents using FastQL and GraphQL-core on the same interpreter, with source locations enabled for both. Each workload receives warm-up iterations and multiple timed samples; the median is used. The gate requires FastQL to be faster on every workload and `sum(oracle medians) / sum(FastQL medians) >= 1.5`.

The benchmark runs in a dedicated CI job across supported Python versions and during release verification, isolated from unit-test timing. Absolute latency thresholds and single-sample comparisons are rejected as too sensitive to runner variation. Benchmark fixtures and iteration counts are versioned so changes require review.

### Monitor upstream releases without automatic adoption

A weekly scheduled workflow will compare the pinned GraphQL.js and GraphQL-core versions in the conformance manifest with their latest stable releases. When either changes, it opens or updates one maintenance issue containing release links and fails the monitoring job until the manifest records an explicit disposition: upgrade in a dedicated change or defer with a review date and rationale.

The workflow does not rewrite fixtures, dependencies, or specification claims. Automatic upgrades are rejected because parser grammar and diagnostics changes require compatibility and performance review.

## Risks / Trade-offs

- [September 2025 behavior can differ from GraphQL.js 16.14.1] -> Treat the specification as normative and require narrowly documented oracle divergences with direct specification citations.
- [Imported tests can drift or violate attribution requirements] -> Commit provenance, checksums, source commit, license notice, deterministic generation, and exclusion classifications.
- [Differential tests can overfit GraphQL-core implementation details] -> Compare semantic AST projections and error categories/positions, not Python types or exact messages.
- [Depth semantics can be confused with query complexity] -> Name and document it as syntactic parser depth and keep semantic cost analysis out of scope.
- [Catching recursion can conceal parser defects] -> Use explicit nesting guards first and retain a narrow top-level `RecursionError` translation only as a final safety boundary with regression coverage.
- [Timing gates can be noisy] -> Use same-process ratios, warm-ups, medians, fixed fixtures, and a dedicated benchmark job; investigate repeated failures rather than weakening thresholds automatically.
- [Conformance work can expand indefinitely] -> Fix the specification/version scope and require explicit changes for SDL, experiments, or new upstream releases.
- [Stricter parsing rejects previously accepted malformed traffic] -> Document corrections, add precise source errors, and preserve all valid existing inputs and public AST contracts.

## Migration Plan

1. Establish baseline correctness and performance results, add the version/provenance manifest, and pin development-only oracle/tooling dependencies.
2. Import applicable upstream fixtures and build normalization/differential infrastructure before changing parser behavior.
3. Correct lexical behavior and diagnostics, adding minimized regressions for every observed mismatch.
4. Align parser productions, locations, and resource controls, then propagate schema limits through all string-query entry points.
5. Add deterministic property tests, scheduled fuzzing, benchmark gates, release monitoring, and public documentation.
6. Run focused language/integration suites, the full test matrix, package metadata checks, OpenSpec validation, and release benchmarks.

Rollback is behavioral: individual parser corrections can be reverted behind their regression cases, and schema limits default to `None`. Development tooling and fixtures can remain even if a specific correction is rolled back. Runtime dependency and public AST compatibility are unchanged throughout.

## Open Questions

None. The specification target, executable-only scope, development oracle, public compatibility constraints, default-unlimited policy, conformance process, and performance threshold are fixed for this change.
