## Why

FastQL's core (parse → build → validate → execute) is solid, but it is not yet
viable for real-world production deployments: it has no N+1 mitigation, no
real-time subscriptions, no schema-level observability hooks, no federation, and
no Relay-style pagination — all of which Strawberry GraphQL provides and which
production teams expect. This change defines the roadmap that closes the gap to a
production-grade, "real-case-integration-ready" package while preserving FastQL's
defining traits: a hand-built engine, type-hint-driven authoring, and a
dependency-free, web-framework-agnostic core.

## What Changes

Organized into four phases (priority clusters — DataLoader, subscriptions,
federation, Relay — lead the roadmap). All new heavy/optional dependencies stay
behind `pyproject.toml` extras; the core remains import-clean.

**Phase 1 — Core production hardening**
- Add `DataLoader` with per-request batching + caching, accessible via `Info`/context.
- Add a `SchemaExtension` lifecycle system (`on_operation/on_parse/on_validate/on_execute`, `resolve` wrap) as the foundation for tracing, masking, and metrics.
- Implement real **subscription execution** (async-generator resolvers yielding a stream of `ExecutionResult`s).
- Complete query **validation** rules (fragment cycles, known/located directives, possible fragment spreads, lone-anonymous-operation, unique-name rules, overlapping-fields-can-be-merged).
- Polish error handling: per-error `extensions` and a configurable **masking policy**.
- Add a native `GraphQLTestClient` test utility and a `fastql export-schema` CLI command (SDL + introspection JSON to file).

**Phase 2 — Advanced type authoring**
- Add **generic types** (`TypeVar`/`Generic[T]`) with synthetic per-parametrization type generation.
- Add **Relay** support: `Node` interface, global IDs, `Connection/Edge/PageInfo`, cursor pagination helpers (builds on generics).
- Add **custom directive** authoring (`@Directive` with locations; applied to schema/type-system).
- Add **field visibility** markers: private (excluded from schema) and external (federation) fields.
- Add per-member **enum customization** (name/description/deprecation) — modifies `schema-definition`.

**Phase 3 — Distributed & transport**
- Add **Apollo Federation v2**: `_service`/`_entities`, `@key/@external/@shareable/@requires/@provides/@inaccessible`, entity reference resolvers, federated SDL.
- Add **subscription transport** over the wire: `graphql-transport-ws` WebSocket, SSE, and multipart — in the integrations layer.
- Add **file uploads** (graphql-multipart-request-spec) — in the integrations layer.
- Add **query batching** (JSON array of operations) — modifies `http-integration-contract`.
- Add **tracing/instrumentation** (OpenTelemetry + Apollo-style tracing extension) built on the extension system.

**Phase 4 — Ecosystem**
- Add **Pydantic** model → GraphQL type conversion (optional extra).
- Add **incremental delivery** (`@defer`/`@stream`).
- Add **additional framework adapters**: AIOHTTP, Sanic, Litestar, Quart, Django Channels.

## Capabilities

### New Capabilities
- `data-loaders`: Per-request batch-loading utility (batch fn, keyed cache, dedup) accessible from resolvers to eliminate N+1.
- `schema-extensions`: Schema-level lifecycle hook system wrapping parse/validate/execute/operation and resolver calls.
- `subscription-execution`: Async-generator subscription resolution producing a stream of execution results.
- `subscription-transport`: Over-the-wire subscription delivery (graphql-transport-ws WebSocket, SSE, multipart) in integrations.
- `generic-types`: `Generic[T]`/`TypeVar` parametric types compiled to concrete synthetic GraphQL types.
- `relay-pagination`: `Node` interface, global object IDs, `Connection/Edge/PageInfo`, cursor pagination helpers.
- `apollo-federation`: Federation v2 subgraph support — entities, federation directives, `_service`/`_entities`, federated SDL.
- `custom-directives`: Author-defined schema directives with declared locations and SDL rendering.
- `field-visibility`: Private (schema-excluded) and external (federation) field markers.
- `query-batching`: Execute a JSON array of operations in one HTTP request.
- `file-uploads`: graphql-multipart-request-spec uploads mapped to an `Upload` scalar.
- `tracing-instrumentation`: OpenTelemetry spans and Apollo-style tracing as schema extensions.
- `incremental-delivery`: `@defer`/`@stream` incremental result payloads.
- `pydantic-integration`: Generate FastQL types/inputs from Pydantic models.
- `testing-utilities`: `GraphQLTestClient` for executing operations against a schema in tests.
- `schema-export-cli`: `fastql export-schema module:schema` writing SDL / introspection JSON.

### Modified Capabilities
- `query-validation`: Add the missing GraphQL validation rules for spec-completeness.
- `query-execution`: Add per-error `extensions`, a configurable error-masking policy, and a subscription execution entrypoint hook.
- `schema-definition`: Add per-member enum value customization (name/description/deprecation) to the authoring surface.

## Impact

- **New core modules:** `fastql/dataloader.py`, `fastql/extensions.py`, `fastql/relay.py`, `fastql/federation/`, `fastql/directives.py`, `fastql/testing.py`; execution gains a subscription path and extension hooks.
- **Modified core:** `execution/execute.py`, `execution/values.py`, `validation/rules.py`, `decorators/*`, `schema_builder.py`, `types/definition.py`, `context.py`, `errors.py`, `sdl.py`, `introspection.py`, `cli.py`.
- **Integrations:** `fastql/integrations/*` gain subscription transport, file upload, query batching; new adapter modules added.
- **Packaging:** new optional extras in `pyproject.toml` (`[pydantic]`, `[opentelemetry]`, `[aiohttp]`, `[sanic]`, `[litestar]`, `[quart]`, `[channels]`); base install stays dependency-free.
- **Docs/specs:** new pages under `docs/` and updated OpenSpec specs; new tests under `tests/` mirroring existing layout.

## Non-goals / out of scope

- No rewrite of the existing engine, authoring API, or DI model — these are additive extensions.
- The dependency-free, web-framework-agnostic **core** is preserved: all transport (WebSocket/SSE/multipart) and heavy ecosystem features live in the integrations layer or behind optional extras, consuming `build_schema()`/`execute()`.
- Not adopting `graphql-core` or any runtime dependency in the base package.
- Federation v1, persisted queries, automatic persisted queries (APQ), and a hosted gateway are out of scope for this change.
