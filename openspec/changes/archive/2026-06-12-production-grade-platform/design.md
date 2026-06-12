## Context

FastQL has a working hand-built engine (lexer → parser → validator → async
executor), type-hint-driven authoring, DI/context, introspection, SDL, a dev
server, and five web-framework adapters — all with a dependency-free,
web-framework-agnostic core. To be production-ready for real integrations it must
close the gap to Strawberry's documented feature set: N+1 mitigation,
observability hooks, real-time subscriptions, federation, Relay pagination, and
more.

This is a roadmap change implemented in four phases. The defining constraints are
non-negotiable: (1) the base package stays dependency-free; (2) the core imports
no web framework — all transport lives in `fastql/integrations/`; (3) every
feature is additive — no rewrite of the engine, authoring API, or DI model.

## Goals / Non-Goals

**Goals:**
- Provide the production capabilities listed in the proposal, each behind a clean, type-hint-first authoring surface consistent with existing decorators.
- Establish a `SchemaExtension` lifecycle as the single foundation for tracing, masking, metrics, and (future) caching.
- Keep heavy/optional dependencies (Pydantic, OpenTelemetry, extra frameworks) behind `pyproject.toml` extras with lazy imports.
- Preserve backward compatibility of existing public APIs (`execute`, `build_schema`, `Schema`, decorators).

**Non-Goals:**
- No adoption of `graphql-core` or any base runtime dependency.
- No transport code in the core; WebSocket/SSE/multipart live in integrations.
- No Federation v1, persisted queries/APQ, or a hosted gateway.
- No engine rewrite — generics/relay/federation are layered on the existing IR.

## Decisions

### D1 — Extension system as the observability backbone
A `SchemaExtension` base with `on_operation/on_parse/on_validate/on_execute`
(generator-style enter/exit) plus a `resolve(next_, source, info, **args)` wrapper,
registered on `Schema(extensions=[...])`. Tracing (OTel, Apollo) and error masking
are implemented as extensions rather than bespoke executor branches.
- **Why over ad-hoc hooks:** one composable mechanism mirrors Strawberry, avoids scattering instrumentation through `execute.py`, and reuses the existing `FieldExtension` wrapping pattern in `execution/execute.py:407`.
- **Alternative considered:** callback parameters on `execute()` — rejected as non-composable and hard to order.

### D2 — DataLoader as a standalone, request-scoped utility
`fastql/dataloader.py` with `DataLoader(batch_load_fn, max_batch_size, cache)`.
Batching uses the event loop: `load()` enqueues a key + future and schedules a
dispatch via `loop.call_soon`/a pending-batch task; the batch resolves all futures.
Loaders are placed on the per-request `Context` (and reachable via `Info`), so the
cache is naturally request-scoped.
- **Why:** matches Strawberry/DataLoader semantics; ties into the existing `Context`/`Info` DI without engine changes.
- **Alternative:** auto-batching sibling resolver calls in the executor — rejected as implicit/surprising and harder to control.

### D3 — Subscriptions: async-generator execution + transport split
Core gains `subscribe()` in `execution/` that calls the root subscription resolver
to get an async iterator, then re-executes the selection set per yielded value
producing an async stream of `ExecutionResult`. Transport (graphql-transport-ws,
SSE, multipart) lives entirely in `fastql/integrations/` consuming `subscribe()`.
- **Why:** keeps the streaming protocol out of the core, honoring the agnostic-core rule; single-root-field validation enforced in `validation/`.
- **Alternative:** push websockets into core — rejected (violates D's core constraint).

### D4 — Generics via concrete type synthesis at build time
Generic `@Type(Generic[T])` classes are templates; when referenced as `Conn[User]`,
`schema_builder` synthesizes one concrete `ObjectType` per unique parametrization,
named by convention (`UserConnection`) with overridable naming, memoized in the
registry. Builds on the existing thunk/`TypeReference` resolution at
`schema_builder.py:236`.
- **Why:** GraphQL has no generics — concrete synthesis is the only spec-valid approach and is what Strawberry does.
- **Alternative:** erase to `JSON`/`Any` — rejected (loses type safety/introspection).

### D5 — Relay built on generics + a Node registry
`fastql/relay.py` provides `Node` interface, global-ID codec (base64 of
`Type:id`), `Connection[T]/Edge[T]/PageInfo`, and a `connection_from_list`-style
slicing helper. The root `node(id)` query uses a type→resolver registry to fetch
by decoded global ID. Depends on D4.

### D6 — Federation as a build-time SDL/entity layer
`fastql/federation/` adds federation directives (applied-directive metadata on the
IR), a federated-SDL printer extending `sdl.py` with the `@link` header, and the
`_service`/`_entities` root fields plus a per-type reference-resolver registry.
Uses `field-visibility` (`@external`) and `custom-directives`. No engine change —
entities resolve through ordinary resolvers over the `_Any` scalar.

### D7 — Transport concerns extend the shared HTTP handler
Query batching (array bodies), file uploads (multipart parsing → `Upload` scalar),
and SSE are added to `fastql/integrations/http.py`'s shared handler and surfaced
through each adapter, keeping per-framework code thin (consistent with the existing
`GraphQLHTTPHandler` contract at `integrations/http.py:176`).

### D8 — Optional dependencies isolated behind extras
Pydantic, OpenTelemetry, and additional adapters (aiohttp/Sanic/Litestar/Quart/
Channels) are new `pyproject.toml` extras with lazy imports and import-guard tests,
mirroring the existing `integration-packaging` rules.

### D9 — Validation completeness as additive rules
New rules (fragment cycles, known/located directives, possible spreads,
lone-anonymous-operation, uniqueness, overlapping-fields-can-be-merged) are added
to `validation/rules.py` as independent rule functions — no change to existing rule
behavior, so they are ADDED requirements.

## Risks / Trade-offs

- **Generics/Relay/Federation interactions are complex** → Build in dependency order (generics → relay; visibility+directives → federation); land each with focused tests before the next.
- **DataLoader batching timing bugs (futures resolved out of tick)** → Use a well-tested dispatch pattern (pending batch + `call_soon`), with explicit tests for dedup, batch-size chunking, and per-key errors.
- **Subscription resource leaks** → Guarantee `aclose()` on the source generator on cancel/disconnect; cover with cancellation tests.
- **Overlapping-fields-can-be-merged is the hardest validation rule** → Implement incrementally; ship a correct subset first, expand with conformance cases.
- **Extension overhead on hot resolver path** → Make the `resolve` wrapper a no-op fast path when no extensions are registered.
- **Scope is large** → Phased delivery; each phase is independently shippable and testable; later phases can be split into follow-up changes if needed.

## Migration Plan

- All changes are additive; no breaking API changes. Existing schemas/resolvers keep working unchanged.
- Roll out by phase (1 → 4). Each capability ships with tests under `tests/`, docs under `docs/`, and promotion of its spec into `openspec/specs/` at archive time.
- New extras are opt-in; the default `pip install fastql` remains dependency-free.
- Rollback: features are isolated modules/extras and can be reverted independently without affecting the core.

## Open Questions

- Defer/Stream wire format: target the GraphQL incremental-delivery `multipart/mixed` shape vs. a simpler custom envelope? (Lean: spec-aligned multipart.)
- WebSocket protocol scope: ship `graphql-transport-ws` first and treat legacy `graphql-ws` as optional/later?
- Global-ID encoding: opaque base64 (default) vs. pluggable codec — expose customization now or later?
- Pydantic v1 vs v2 support matrix — target v2 only initially?
