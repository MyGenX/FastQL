## 1. Baseline and Language Contract

- [ ] 1.1 Add a public parser compatibility constant and documentation declaring GraphQL September 2025 executable documents as the supported scope, with SDL and experimental grammar explicitly excluded.
- [ ] 1.2 Add `graphql-core==3.2.11` and Hypothesis to development-only dependencies, record the GraphQL.js 16.14.1 correspondence, and verify neither dependency enters base wheel metadata.
- [ ] 1.3 Create versioned small, medium, and large benchmark fixtures plus a command that captures warmed median FastQL and GraphQL-core parse timings on the same interpreter.
- [ ] 1.4 Record the current lexer/parser acceptance, diagnostics, recursion, and benchmark baseline so subsequent corrections and performance changes are reviewable.
- [ ] 1.5 Add pytest coverage for the published compatibility target, SDL rejection, development dependency isolation, and reproducible baseline fixture loading.

## 2. GraphQL.js Conformance Corpus

- [ ] 2.1 Add `tests/conformance/graphql_js/` with a manifest recording GraphQL.js 16.14.1, immutable source commit/URLs, selected language tests, checksums, import timestamp, license notice, and fixture format version.
- [ ] 2.2 Implement a manual corpus-update script that fetches an explicitly requested immutable GraphQL.js tag/commit, verifies provenance, and translates lexer/parser cases into deterministic committed fixtures.
- [ ] 2.3 Classify every imported case as applicable executable syntax, SDL, experimental, harness-only, or intentionally divergent, with exact reasons for every exclusion.
- [ ] 2.4 Implement fixture runners for token streams, decoded values, accepted ASTs, rejected inputs, source offsets, and parse-print-parse cases without requiring network access or Node.js in normal CI.
- [ ] 2.5 Add pytest coverage for manifest validation, checksums, license/provenance presence, deterministic regeneration, offline fixture execution, and rejection of unclassified cases.

## 3. Differential Oracle Harness

- [ ] 3.1 Implement normalized FastQL and GraphQL-core token projections covering kind, decoded value, start/end offsets, line, and column.
- [ ] 3.2 Implement normalized AST projections covering node kind, semantic fields, descriptions, values, child order, and locations while normalizing list/tuple and operation string/enum differences.
- [ ] 3.3 Implement rejection normalization for lexical versus syntactic category and absolute source position without comparing exact English error wording.
- [ ] 3.4 Add a reviewed fixture-ID allowlist format requiring a specification-based rationale for every intentional oracle difference.
- [ ] 3.5 Run all applicable corpus cases through both implementations and report concise structural diffs for acceptance, decoding, AST, location, and rejection mismatches.
- [ ] 3.6 Add pytest coverage proving each mismatch class fails, exact allowlisted differences pass, stale allowlist entries fail, and the existing literal parser corpus has no unexplained acceptance mismatch.

## 4. Lexer Conformance Corrections

- [ ] 4.1 Implement fixed-width and variable-width Unicode escape parsing, valid surrogate-pair composition, and rejection of isolated or invalid surrogate escapes at the correct offset.
- [ ] 4.2 Reject prohibited unescaped control characters in regular and block strings while preserving valid escaped controls and escaped triple quotes.
- [ ] 4.3 Align block-string raw-value scanning, line-ending normalization, common indentation, and leading/trailing blank-line removal with September 2025 behavior.
- [ ] 4.4 Strengthen number scanning for leading zeros, required fraction/exponent digits, signs, numeric-name adjacency, and first-invalid-character diagnostics.
- [ ] 4.5 Verify ignored BOMs, whitespace, commas, comments, CR/LF/CRLF handling, punctuators, token spans, lookahead, and EOF locations against the imported corpus.
- [ ] 4.6 Add focused pytest and differential regression coverage for every corrected Unicode, string, block-string, number, ignored-token, and source-location scenario.

## 5. Parser Grammar, AST, and Diagnostics

- [ ] 5.1 Add optional trailing `description` fields to operation, fragment-definition, and variable-definition AST classes without breaking existing positional constructors or undescribed printer output.
- [ ] 5.2 Parse September 2025 descriptions for named operations, fragment definitions, and variable definitions; reject descriptions on query shorthand; and preserve descriptions through printing and reparsing.
- [ ] 5.3 Audit every executable grammar production for required non-empty lists, const-value variable exclusion, fragment-name restrictions, operation forms, directives, values, and type references.
- [ ] 5.4 Centralize expected-token and unexpected-token classification so lexical/syntax errors identify the first offending position consistently.
- [ ] 5.5 Add an explicit parser nesting guard for all recursive selection, value-container, and list-type productions plus a narrow top-level safety translation so raw `RecursionError` cannot escape.
- [ ] 5.6 Add pytest and differential coverage for described definitions, all executable productions, malformed/truncated documents, location spans, printer round trips, and deep-input safety.

## 6. Configurable Token and Depth Limits

- [ ] 6.1 Extend `SchemaConfig` with `max_query_tokens` and `max_query_depth`, both defaulting to `None`, and reject booleans, non-integers, zero, and negative values.
- [ ] 6.2 Extend `parse` and `Parser` with keyword-only token/depth options while preserving existing source-only calls and public imports.
- [ ] 6.3 Count significant lexer tokens excluding ignored input and SOF/EOF, and raise a located `GraphQLSyntaxError` before returning a token beyond the configured limit.
- [ ] 6.4 Count root and nested selection sets, list/object values, and list type references through the shared depth guard, raising at the opening token that exceeds the configured limit.
- [ ] 6.5 Propagate schema limits through execute, incremental execution, subscribe, shared HTTP operation classification/incremental scanning, WebSocket setup, testing clients, and federation field-set parsing where schema configuration is available.
- [ ] 6.6 Add pytest coverage for valid boundaries, one-over-limit failures, ignored-token counting, mixed nesting, invalid configuration, unlimited defaults, pre-parsed AST bypass, and every string-query integration path.

## 7. Property, Mutation, and Fuzz Testing

- [ ] 7.1 Build deterministic Hypothesis strategies for names, numbers, whitespace, comments, regular/block strings, Unicode escapes, scalar/list/object values, variables, directives, fragments, operations, and type references.
- [ ] 7.2 Build malformed-input mutation strategies for truncation, delimiter imbalance, invalid escapes, numeric suffixes, prohibited controls, invalid token adjacency, and malformed fragment/spread constructs.
- [ ] 7.3 Run generated valid and invalid inputs through the differential harness with bounded sizes, fixed CI profiles, reproducible seeds, and parser resource limits.
- [ ] 7.4 Add a regression-fixture workflow that records every minimized failure with expected FastQL/oracle outcomes and prevents resolved cases from being removed accidentally.
- [ ] 7.5 Add scheduled and manually dispatched extended fuzz jobs with larger example counts and upload minimized failing inputs as CI artifacts.
- [ ] 7.6 Add pytest coverage for strategy invariants, deterministic CI profiles, mutation-category reachability, regression replay, and serialization of minimized failures.

## 8. Performance, Release Monitoring, and Completion

- [ ] 8.1 Finalize the benchmark runner with warm-ups, multiple samples, median reporting, locations enabled, fixed iterations, and per-workload plus aggregate ratios.
- [ ] 8.2 Add a dedicated supported-Python CI benchmark matrix that fails unless FastQL is faster on every fixture and `sum(oracle medians) / sum(FastQL medians) >= 1.5`.
- [ ] 8.3 Add a weekly GraphQL.js/GraphQL-core stable-release monitor that opens or updates one maintenance issue and requires an upgrade or time-bounded deferral decision without modifying code automatically.
- [ ] 8.4 Add package-build and isolated-install checks proving runtime metadata and imports remain free of GraphQL-core, Hypothesis, corpus tooling, and benchmark dependencies.
- [ ] 8.5 Update parser architecture, compatibility, configuration, conformance-maintenance, fuzzing, benchmark, and migration documentation plus the changelog.
- [ ] 8.6 Run imported conformance tests, differential tests, property/regression suites, parser-limit integration tests, focused validation/execution/HTTP/subscription/federation/printer tests, and the complete pytest suite.
- [ ] 8.7 Run the supported-Python benchmark matrix, build wheel/sdist artifacts, inspect dependency metadata, and validate `harden-custom-graphql-parser` with OpenSpec.
