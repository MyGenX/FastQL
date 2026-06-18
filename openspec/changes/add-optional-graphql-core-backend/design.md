## Context

FastQL currently has one operation pipeline: source text is parsed into FastQL AST, validated against the FastQL type-system IR, and executed by the FastQL async executor. This preserves a zero-dependency installation and performs well, but users cannot opt into GraphQL-core's native AST, visitor/type utilities, standard validation suite, middleware, or ecosystem compatibility without bypassing FastQL's schema authoring and resolver features.

Supporting two native AST types inside the existing validator and executor would spread backend-specific branches throughout field collection, coercion, validation, execution, extensions, federation, HTTP inspection, and subscriptions. Converting GraphQL-core AST into FastQL AST would preserve one executor but would not provide native GraphQL-core validation/execution and would add measured conversion overhead. The integration therefore needs a higher boundary: a schema selects one complete operation backend, and only FastQL result/error/context contracts cross that boundary.

This change follows `harden-custom-graphql-parser`. That change keeps FastQL as the default, adds shared token/depth configuration, and establishes the custom parser's explicit language contract. GraphQL-core 3.2 is an optional alternative contract, not a replacement or fallback.

## Goals / Non-Goals

**Goals:**

- Preserve the default zero-dependency FastQL parser, validator, executor, subscriptions, and incremental delivery.
- Allow one operation backend to be selected per schema through `SchemaConfig`.
- Provide a stable GraphQL-core 3.2 backend using native schema, AST, validation, execution, subscriptions, middleware, visitors, and utilities.
- Preserve FastQL resolver injection, contexts, permissions, extensions, custom scalars, uploads, masking, and result formatting in GraphQL-core mode.
- Keep framework adapters backend-neutral by routing them through shared operation inspection and execution APIs.
- Expose the compiled GraphQL-core schema and native utilities as a supported optional integration API.

**Non-Goals:**

- Per-request backend switching, automatic fallback, mixed AST execution, or implicit AST conversion.
- Replacing `fastql.parse`, `fastql.language`, FastQL SDL rendering, or the FastQL type-system IR.
- Exact equality of backend ASTs, diagnostics, validation messages, introspection ordering, or coercion wording.
- GraphQL-core 3.3 prereleases or incremental GraphQL-core execution.
- Making arbitrary GraphQL-core schema mutation automatically synchronize back into FastQL IR.

## Decisions

### Select one complete operation backend per schema

Add a public zero-dependency `OperationBackend` protocol and a built-in `FastQLOperationBackend`. The protocol owns source/document recognition, parse, operation selection/inspection, validation, query/mutation execution, subscription execution, incremental capability reporting, and result/error normalization.

`SchemaConfig.operation_backend` accepts `"fastql"`, `"graphql-core"`, or an `OperationBackend` object and defaults to `"fastql"`. Schema construction resolves and stores one backend on the schema. Unknown names or structurally invalid objects raise `ValueError`. Resolving `"graphql-core"` imports the optional integration only when that schema is built; if unavailable, construction raises an actionable `ImportError` naming `fastql[graphql-core]`.

This is preferred over a per-call flag because HTTP, subscriptions, testing utilities, pre-parsed documents, extensions, and schema caching must agree on one engine. Supporting parser-only selection is rejected because it either requires AST conversion or dual-AST FastQL internals and does not expose GraphQL-core's main benefits.

### Keep lifecycle orchestration above the backend boundary

The public `execute`, `validate`, `subscribe`, and `execute_incremental` entry points resolve `schema.operation_backend`. Execution retains the FastQL lifecycle ordering:

1. `on_operation`
2. backend parse inside `on_parse`
3. backend operation selection and validation inside `on_validate`
4. backend query/mutation or subscription execution inside `on_execute`
5. FastQL extension-result collection and result normalization

The FastQL backend wraps the existing parser, validation rules, executor, and subscription implementation with no intended behavior change. The GraphQL-core backend calls native `parse`, `validate`, `execute`, and `subscribe`; it never invokes FastQL validation or field execution.

Standalone `validate(schema, document)` also dispatches through the selected backend. HTTP operation-type checks, batching subscription checks, incremental-directive detection, WebSocket setup, and testing clients call backend-neutral inspection/execution APIs rather than importing a parser directly.

### Treat documents as backend-owned values

Each backend declares the source and document classes it owns. Strings and FastQL `Source` values can be parsed by either backend; GraphQL-core mode converts FastQL `Source` metadata into a native source. Native GraphQL-core `Source` and `DocumentNode` values are accepted only by GraphQL-core mode, while FastQL AST is accepted only by FastQL mode.

A foreign pre-parsed document produces a normalized `BackendDocumentError` naming the selected backend and expected document type. Execution returns it as an unexecuted `ExecutionResult`; standalone validation returns it in the error list. No implicit document conversion or fallback occurs.

`fastql.parse()` and `fastql.language` remain FastQL-only. Native parsing is explicitly imported from `fastql.integrations.graphql_core` or invoked through `GraphQLCoreBackend.parse`.

### Provide a typed GraphQL-core backend object

`GraphQLCoreBackend` accepts stable GraphQL-core 3.2 options:

- `middleware=()`
- `validation_rules=None`, where `None` means GraphQL-core's specified rules and an explicit collection replaces them
- `max_validation_errors=None`
- `max_coercion_errors=50`
- `execution_context_class=None`
- `is_awaitable=None`

The `"graphql-core"` shortcut creates a default instance. GraphQL-core field/type resolvers are not replaceable through these options because FastQL resolver adaptation is required to preserve schema semantics. Advanced users can implement a separate `OperationBackend` if they need a fundamentally different execution contract.

The integration module re-exports the stable native `parse`, `validate`, `visit`, `print_ast`, and schema utility namespace, plus `native` as the imported GraphQL-core package. These direct native utilities return native values and do not apply FastQL normalization or schema limits unless the user calls the backend methods.

### Lazily compile and cache a native GraphQLSchema

`to_graphql_schema(schema, *, rebuild=False)` converts the complete FastQL IR into a GraphQL-core `GraphQLSchema`. Conversion uses identity-aware lazy thunks so circular object/interface/input references resolve without duplicate native types. The converter maps:

- object, interface, union, enum, input-object, scalar, list, and non-null types;
- query, mutation, and subscription roots plus explicitly included orphan types;
- field/argument/input descriptions, defaults, Python output names, deprecations, scalar URLs, enum Python values, directives, locations, and repeatability;
- object `is_type_of`, interface/union `resolve_type`, custom scalar coercion, input-object Python construction/default factories, federation support types/fields, and upload variables.

GraphQL-core built-in scalars and introspection types are used for their reserved names. FastQL-generated `__` types and meta-fields are excluded so GraphQL-core supplies its native introspection system. Native type/field `extensions` retain references to the originating FastQL IR values for resolver and tooling interoperability.

The compiled schema is attached privately to the FastQL schema and reused by backend instances because middleware/validation options do not alter type conversion. `invalidate_graphql_schema(schema)` removes it; `rebuild=True` invalidates then recompiles. Mutation of FastQL IR after first compilation is unsupported until invalidated. Mutating the returned native schema is visible to GraphQL-core operations but is not reflected in FastQL SDL or IR and is documented as advanced backend-local behavior.

### Adapt resolvers without changing native AST execution

Compiled GraphQL fields use resolver wrappers that locate per-execution state from a `ContextVar`. GraphQL-core receives the original user context as `context_value`, so native middleware and resolvers inspecting `GraphQLResolveInfo.context` see the same object passed to FastQL. The context variable carries the FastQL schema, root value, instantiated schema extensions, error-mask policy, dependency cache, root-instance cache, and selected-operation compatibility projection. Query execution sets/reset this state around the native await; subscription execution wraps both stream creation and each iterator step so state remains available for every event without leaking across tasks.

Resolver wrappers construct the existing FastQL `Info` object from native resolve info, including FastQL parent type/field references, path, variables, schema, original context, and root value. The selected native operation and field nodes are projected only for `ExtensionExecutionContext.operation`, `Info.operation`, and `Info.selected_fields` compatibility; these projections never feed GraphQL-core validation or execution.

The wrapper preserves the existing order inside GraphQL-core middleware: native middleware wraps the compiled field resolver; the compiled resolver enforces FastQL permissions, then field extensions, schema `resolve` extensions, dependency injection, owner/root instantiation, and the user resolver. `GraphQLArgument.out_name`, `GraphQLInputField.out_name`, and `GraphQLInputObjectType.out_type` preserve Python argument names, input classes, and default factories. Subscription root fields use a native `subscribe` wrapper for the source iterator and an identity event resolver before executing nested fields.

Custom scalar `parse_literal` converts only the native value-node subtree at that scalar boundary into the equivalent FastQL value AST before calling the existing hook. This narrow adapter preserves custom scalar APIs without converting operation documents.

### Normalize results and errors at public boundaries

GraphQL-core `ExecutionResult` values are converted into FastQL `ExecutionResult`. Errors become FastQL `GraphQLError`/`GraphQLSyntaxError` values preserving message, locations, path, extensions, and original error where available. Parse or validation failures set `executed=False`; field/runtime failures retain partial data and `executed=True`.

FastQL error masking runs during normalization: explicit FastQL/GraphQL-core GraphQL errors retain their messages, while unexpected resolver errors use the configured mask message and keep the original error for logging. Lifecycle extension results are merged after backend results using the existing FastQL precedence.

GraphQL-core validation/coercion wording and introspection ordering remain native. Tests compare response shape and semantic outcomes, not exact cross-backend text.

### Apply parser limits consistently but keep native language contracts

GraphQL-core mode passes `SchemaConfig.max_query_tokens` to native `parse`. After parsing, it applies the shared FastQL syntactic-depth definition through a native AST visitor and reports excess depth as a normalized syntax error. FastQL mode continues enforcing both limits during custom parsing. Direct re-exported native `parse` remains an unwrapped GraphQL-core utility and uses only arguments explicitly supplied by its caller.

Backend inspection uses the selected backend's native document to determine operation type and incremental-directive presence. It may parse separately from later execution, matching current HTTP behavior; no cross-request document cache is introduced in this change.

### Keep incremental execution backend-specific and explicit

`FastQLOperationBackend.supports_incremental` is true and retains current `@defer`/`@stream` streaming. `GraphQLCoreBackend.supports_incremental` is false on the stable 3.2 line. Calling `execute_incremental` with that backend yields one terminal payload containing an actionable error and `hasNext: false`; it never falls back or imports prerelease APIs.

Regular non-streaming `execute` may accept converted `@defer`/`@stream` directive definitions and resolve the operation as one complete response, preserving the existing non-streaming collapse contract. HTTP streaming detection routes an incremental request to `execute_incremental`, where the explicit unsupported result is produced.

### Package the integration as an isolated optional extra

Add `graphql-core = ["graphql-core~=3.2.0"]` and include it in the aggregate `all` extra. Base `fastql` and `fastql.integrations` imports do not import GraphQL-core. Importing `fastql.integrations.graphql_core` or selecting its shortcut without the dependency raises an actionable message.

Stable 3.2 minor releases are accepted; 3.3 prereleases are excluded. Isolated-install tests verify base, GraphQL-core-only, and aggregate-extra metadata/import behavior.

## Risks / Trade-offs

- [Schema conversion misses a FastQL semantic] -> Maintain a conversion matrix and parity tests for every IR type, resolver feature, directive, upload, federation field, and subscription path.
- [Two operation engines produce different diagnostics or coercion details] -> Document backend contracts and assert normalized shape/semantic outcomes rather than exact text parity.
- [ContextVar state leaks or disappears during subscriptions] -> Reset with tokens, wrap every async-iterator step, and test concurrent operations, cancellation, nested execution, and cleanup.
- [FastQL schema mutation leaves a stale native cache] -> Document immutability after compilation, expose invalidation/rebuild APIs, and test stale-versus-rebuilt behavior explicitly.
- [Native middleware expects FastQL resolver internals] -> Define GraphQL-core middleware as native and outermost; expose original context and compiled schema metadata while keeping FastQL hooks inside the resolver wrapper.
- [GraphQL-core introspection differs from FastQL introspection] -> Treat native introspection as a backend feature and test required schema semantics rather than ordering or implementation-specific descriptions.
- [Optional dependency accidentally enters the base import graph] -> Keep all GraphQL imports inside the integration package and enforce isolated wheel/import tests.
- [Active parser-hardening and federation changes overlap] -> Implement after parser hardening and rebase schema/directive conversion on the finalized federation IR before completion.
- [Custom backends broaden the public maintenance surface] -> Keep the protocol operation-focused, runtime-checkable, documented, and covered by a minimal fake-backend contract suite.

## Migration Plan

1. Complete and archive `harden-custom-graphql-parser`, then add the backend protocol and wrap the existing pipeline as the default backend without behavior changes.
2. Add schema configuration, backend resolution, document ownership, dispatch in validation/execution/subscription, and backend-neutral HTTP inspection.
3. Add the optional package extra and GraphQL-core schema converter with native schema/cache APIs.
4. Add resolver, input/scalar, lifecycle, result/error, and subscription adapters.
5. Add incremental rejection, parser-limit parity, native utility exports, documentation, and isolated packaging tests.
6. Run backend contract, schema parity, transport, subscription, federation, upload, extension, and full regression suites.

Rollback is configuration-safe: `"fastql"` remains the default, and removing the optional backend does not alter stored schema definitions or FastQL documents. Users migrate to GraphQL-core mode by installing the extra and changing one schema configuration value; they return by restoring `"fastql"` and removing the optional dependency.

## Open Questions

None. The schema-wide selection model, full-pipeline delegation, optional-extra packaging, public native schema access, stable 3.2 line, document ownership, and incremental-delivery policy are fixed for this change.
