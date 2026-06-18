## Why

Some FastQL users value the custom engine's speed and zero-dependency installation, while others need GraphQL-core's mature validation rules, native AST/visitor ecosystem, middleware, schema utilities, and compatibility with the wider Python GraphQL ecosystem. A schema-selected operation backend provides both without forcing two AST models through one validator/executor or adding GraphQL-core to the default installation.

## What Changes

- Add a schema-wide operation backend abstraction covering parsing, validation, query/mutation execution, subscriptions, operation inspection, lifecycle integration, and result normalization.
- Keep the current FastQL language, validation, and execution stack as the default `"fastql"` backend with unchanged zero-dependency behavior.
- Add an optional `GraphQLCoreBackend` that lazily compiles the FastQL type-system IR into a cached native GraphQL-core `GraphQLSchema` and delegates the full operation pipeline to GraphQL-core 3.2.
- Add `SchemaConfig(operation_backend="fastql" | "graphql-core" | OperationBackend)`, with a configured backend object supporting GraphQL-core middleware, validation rules, validation/coercion limits, execution context customization, and native schema access.
- Add a `graphql-core` installation extra pinned to the stable `graphql-core~=3.2.0` line and actionable errors when the optional backend is selected without the extra.
- Expose `GraphQLCoreBackend`, `to_graphql_schema`, native language/visitor/validation utilities, compiled-schema access, and cache invalidation from `fastql.integrations.graphql_core` without changing `fastql.parse()` or `fastql.language`.
- Preserve FastQL dependency injection, contexts, permissions, field/schema extensions, sync/async resolvers, custom scalars, uploads, error masking, introspection, subscriptions, and federation runtime fields through schema and resolver adapters.
- Reject pre-parsed documents from the wrong backend with an actionable error instead of converting ASTs implicitly.
- Explicitly reject incremental `@defer`/`@stream` execution in GraphQL-core mode; the implementation SHALL NOT silently fall back to FastQL or depend on GraphQL-core 3.3 prereleases.

### Non-goals / Out of Scope

- Making GraphQL-core a mandatory dependency, replacing the FastQL engine, changing the default backend, or changing top-level FastQL language APIs is out of scope.
- Per-request or per-operation backend switching, implicit AST conversion, and mixed-engine execution within one schema are out of scope.
- Exact equality between backend ASTs, validation messages, coercion wording, execution ordering, or unsupported language extensions is not required; each backend retains its documented contract.
- GraphQL-core incremental execution, GraphQL-core 3.3 prerelease support, and automatic fallback to FastQL are out of scope.
- This change adds no framework-specific backend branches; all transports continue using shared execution/subscription contracts.

## Capabilities

### New Capabilities

- `operation-backends`: Schema-wide operation backend selection, the optional GraphQL-core engine, native integration utilities, schema conversion/cache behavior, backend document ownership, and normalized result/error contracts.

### Modified Capabilities

- `schema-building`: Accept and validate a schema-wide `operation_backend` configuration while preserving `"fastql"` as the default.
- `query-validation`: Route standalone and execution-time validation through the schema-selected backend and reject foreign backend documents.
- `query-execution`: Route parse/validate/execute phases through the selected backend while preserving FastQL result, context, resolver-hook, and masking contracts.
- `subscription-execution`: Route subscriptions through the selected backend and normalize initial and per-event results and cleanup behavior.
- `incremental-delivery`: Define incremental delivery as supported only by the FastQL backend and require an explicit error in GraphQL-core mode.
- `integration-packaging`: Add an isolated `graphql-core` optional extra while keeping the base distribution dependency-free.

## Impact

- Public additions include `SchemaConfig.operation_backend`, an `OperationBackend` protocol, `GraphQLCoreBackend`, native GraphQL-core integration utilities, and the `graphql-core` extra.
- Execution, subscription, HTTP operation inspection, WebSocket handling, testing utilities, lifecycle extensions, and parser-limit propagation will dispatch through the schema-selected backend.
- A new schema converter and resolver adapter layer will map FastQL types/directives/defaults/resolvers to GraphQL-core while normalizing results back to FastQL objects.
- GraphQL-core schemas are compiled lazily and cached; mutating a FastQL schema after compilation requires explicit invalidation and recompilation.
- The change should be implemented after `harden-custom-graphql-parser` so both backends share final token/depth configuration semantics and FastQL remains the documented default.
- Base wheel metadata remains free of GraphQL-core; installing `fastql[graphql-core]` adds the stable GraphQL-core 3.2 runtime only for users selecting that backend.
