## 1. Backend Contract and Schema Configuration

- [ ] 1.1 Complete/rebase onto `harden-custom-graphql-parser`, including final `max_query_tokens` and `max_query_depth` semantics, before changing operation dispatch.
- [ ] 1.2 Add the public runtime-checkable `OperationBackend` protocol, backend capability metadata, and normalized `BackendDocumentError` without importing optional dependencies.
- [ ] 1.3 Implement backend resolution for `"fastql"`, `"graphql-core"`, and backend objects, including actionable unknown-name, invalid-object, and missing-extra errors.
- [ ] 1.4 Extend `SchemaConfig` and built `Schema` with schema-wide backend selection while preserving `"fastql"` as the default through direct and decorator-built schema paths.
- [ ] 1.5 Add a minimal fake backend used to verify protocol dispatch, schema-wide identity, capability reporting, and no per-call backend override.
- [ ] 1.6 Add pytest coverage for default selection, shortcut/object selection, decorated schema propagation, invalid configurations, and base imports without GraphQL-core installed.

## 2. Default FastQL Backend Refactor

- [ ] 2.1 Implement `FastQLOperationBackend` as a thin wrapper around the existing parser, operation selection, validator, executor, subscriptions, incremental execution, and document types.
- [ ] 2.2 Refactor public `validate`, `execute`, and `subscribe` orchestration to dispatch through `schema.operation_backend` while retaining existing signatures and result types.
- [ ] 2.3 Preserve `on_operation`, `on_parse`, `on_validate`, `on_execute`, schema resolve extensions, masking, and extension-result collection above/inside the backend boundary as designed.
- [ ] 2.4 Add backend-neutral operation inspection for operation type, selected operation, and incremental-directive presence without changing FastQL AST behavior.
- [ ] 2.5 Route `execute_incremental` through backend capabilities while preserving the existing FastQL async payload stream unchanged.
- [ ] 2.6 Add pytest regression coverage proving the default backend matches current parsing, validation, execution, subscription, incremental, extension, error, and performance behavior.

## 3. Optional Package and Public GraphQL-core API

- [ ] 3.1 Add the `graphql-core` optional dependency extra using `graphql-core~=3.2.0`, include it in `all`, and exclude 3.3 prerelease APIs.
- [ ] 3.2 Create the isolated `fastql.integrations.graphql_core` package with lazy dependency loading and installation guidance naming `fastql[graphql-core]`.
- [ ] 3.3 Implement validated `GraphQLCoreBackend` options for middleware, validation rules, validation/coercion limits, execution context class, and awaitable detection, plus the default shortcut instance.
- [ ] 3.4 Re-export supported native `parse`, `validate`, `visit`, `print_ast`, the schema utility namespace, and the GraphQL-core package as `native` without changing top-level FastQL language exports.
- [ ] 3.5 Add pytest coverage for missing-extra failures, stable-version metadata, shortcut defaults, custom options, native utility return types, and top-level import isolation.

## 4. Native GraphQLSchema Conversion and Cache

- [ ] 4.1 Implement lazy identity-aware type conversion and wrapper conversion with thunks for circular object, interface, union, and input-object references.
- [ ] 4.2 Convert roots, orphan types, fields, arguments, Python output names, descriptions, defaults, deprecations, scalar URLs, enum values, and abstract-type hooks.
- [ ] 4.3 Convert input fields using GraphQL-core output names and input-object `out_type`, including Python class construction, renamed fields, static defaults, and per-coercion default factories.
- [ ] 4.4 Convert custom scalar serialize/parse-value hooks and implement the native-value-node to FastQL-value-node adapter used only by custom `parse_literal` hooks.
- [ ] 4.5 Convert directive definitions, argument definitions, locations, repeatability, custom incremental directives, and federation directive definitions while preserving GraphQL-core specified behavior.
- [ ] 4.6 Exclude FastQL-generated introspection types/meta-fields and map reserved built-in scalars to GraphQL-core native built-ins.
- [ ] 4.7 Implement `to_graphql_schema(schema, rebuild=False)`, private per-schema caching, `invalidate_graphql_schema`, source-IR references in native extensions, and explicit rebuild behavior.
- [ ] 4.8 Add pytest coverage for every FastQL IR type, wrappers, circular references, roots/orphans, directives, defaults, descriptions, deprecations, cache reuse/invalidation, and native schema validity.

## 5. Resolver, Context, and Hook Adaptation

- [ ] 5.1 Implement request-scoped GraphQL-core execution state with `ContextVar` token reset, original user context passthrough, dependency/root-instance caches, extension instances, and mask policy.
- [ ] 5.2 Build FastQL `Info` from native resolve info, mapping parent/field IR, Python name, path, variables, schema, context, and root value.
- [ ] 5.3 Project the selected native operation and native field nodes into FastQL AST only for `ExtensionExecutionContext.operation`, `Info.operation`, and `Info.selected_fields` compatibility.
- [ ] 5.4 Adapt field resolvers for Python argument names, owner-bound methods, root/container construction, parent/context/info/dependency injection, defaults, and sync/async results.
- [ ] 5.5 Preserve FastQL permission, field-extension, and schema resolve-extension ordering inside native GraphQL-core middleware.
- [ ] 5.6 Adapt object `is_type_of`, interface/union `resolve_type`, default attribute/dict field resolution, and subscription-root event identity resolution.
- [ ] 5.7 Add pytest coverage for all injection roles, shared async dependencies, root construction, `Info` fields, permissions, field/schema extensions, native middleware ordering, abstract types, and concurrent/nested operation isolation.

## 6. GraphQL-core Parsing, Validation, and Query Execution

- [ ] 6.1 Implement GraphQL-core source/document ownership, FastQL `Source` conversion, native source support, and foreign-document rejection without implicit AST conversion.
- [ ] 6.2 Parse with GraphQL-core's configured token limit and enforce FastQL syntactic-depth semantics through a native AST visitor before validation.
- [ ] 6.3 Implement native operation selection/inspection and normalized operation compatibility views for lifecycle extensions and HTTP policy checks.
- [ ] 6.4 Implement GraphQL-core validation with default specified rules or the configured replacement collection and maximum validation errors.
- [ ] 6.5 Implement native query/mutation execution using the compiled schema, configured middleware/execution options, original context, variables, root value, and operation name.
- [ ] 6.6 Normalize native parse, validation, coercion, and runtime errors into FastQL syntax/error classes with message, locations, path, extensions, original error, and correct `executed` state.
- [ ] 6.7 Apply FastQL unexpected-error masking and merge backend/extension result metadata without losing partial data.
- [ ] 6.8 Add pytest coverage for native strings/sources/documents, foreign documents, token/depth limits, custom validation rules, middleware/options, operation selection, coercion, partial data, extensions, masking, and lifecycle phases.

## 7. GraphQL-core Subscriptions and Incremental Policy

- [ ] 7.1 Compile subscription root fields with separate native source-stream and per-event resolvers while preserving FastQL injection and async-generator semantics.
- [ ] 7.2 Implement GraphQL-core `subscribe` dispatch and normalize initial errors plus every native event `ExecutionResult` into FastQL results.
- [ ] 7.3 Wrap async iteration so request-scoped context state is installed for stream creation and each event, reset afterward, and retained across normal asynchronous scheduling.
- [ ] 7.4 Propagate cancellation and `aclose()` to native/source iterators and release backend state on completion, error, or consumer abandonment.
- [ ] 7.5 Return one terminal `{data: null, errors: [...], hasNext: false}` payload from `execute_incremental` in GraphQL-core mode without fallback or prerelease imports.
- [ ] 7.6 Preserve ordinary non-streaming execution of converted `@defer`/`@stream` documents as one backend-native complete result.
- [ ] 7.7 Add pytest coverage for multi-event streams, initial/per-event errors, context/dependency continuity, cleanup/cancellation, native subscription documents, incremental rejection, and non-streaming incremental directives.

## 8. Shared HTTP, WebSocket, and Testing Integration

- [ ] 8.1 Route HTTP GET mutation policy, batching subscription rejection, operation selection, and incremental detection through backend-neutral inspection with the handler's schema.
- [ ] 8.2 Route normal, streaming subscription, and incremental HTTP execution through the selected backend while preserving existing media types and normalized payloads.
- [ ] 8.3 Ensure GraphQL-over-WebSocket subscriptions use the schema backend, normalize initial/event errors, and retain cancellation cleanup.
- [ ] 8.4 Update `GraphQLTestClient` to remain backend-transparent for query, mutation, and subscription strings and to accept backend-owned pre-parsed documents where public signatures allow.
- [ ] 8.5 Add pytest coverage for GET/POST policy, batching, SSE/multipart behavior, GraphQL-core incremental errors, WebSocket events/cancellation, testing-client parity, and custom backend inspection.

## 9. Feature Parity and Ecosystem Coverage

- [ ] 9.1 Verify GraphQL-core native introspection against converted standard schemas while retaining FastQL SDL/schema endpoint output independent of backend.
- [ ] 9.2 Verify custom scalars, enums, input classes, renamed fields/arguments, Pydantic inputs, uploads through variables, and default factories under both backends.
- [ ] 9.3 Verify FastQL tracing, OpenTelemetry, lifecycle extensions, resolver extensions, permissions, error extensions, and mask policies under GraphQL-core mode.
- [ ] 9.4 Verify federation `_service`, `_entities`, `_Any`, `_Entity`, reference resolution, custom directives, and schema-local metadata after rebasing onto the finalized federation change.
- [ ] 9.5 Add a backend parity matrix covering representative valid responses and error shapes while explicitly allowing backend-native wording, AST, introspection ordering, and validation differences.
- [ ] 9.6 Add pytest coverage for all parity matrix rows and document every intentionally unsupported or backend-specific behavior.

## 10. Packaging, Documentation, and Release Readiness

- [ ] 10.1 Add isolated base, `graphql-core`, and `all` installation tests that inspect wheel metadata and import/execute representative operations.
- [ ] 10.2 Update configuration, execution, subscription, testing, integration, and API documentation with shortcut/backend-object examples, native utility usage, cache invalidation, and document ownership.
- [ ] 10.3 Document backend comparison, GraphQL-core 3.2 compatibility, context/middleware ordering, native schema mutation constraints, incremental limitations, and migration between backends.
- [ ] 10.4 Update public exports, API reference material, changelog, extras documentation, and OpenSpec cross-references to parser hardening and federation changes.
- [ ] 10.5 Run focused backend/schema conversion/resolver/subscription/transport tests, all framework integration tests, package builds, isolated installs, and the complete pytest suite without GraphQL-core installed.
- [ ] 10.6 Run the complete pytest suite with `fastql[graphql-core]`, validate both backend conformance matrices, and confirm no GraphQL-core import occurs in the default path.
- [ ] 10.7 Validate `add-optional-graphql-core-backend` with OpenSpec and confirm all artifacts and release checks are apply-ready.
