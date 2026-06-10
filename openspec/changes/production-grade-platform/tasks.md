# Tasks — production-grade-platform

> Phased per the design. Each phase ends with its own pytest coverage of the
> relevant spec scenarios. Keep the core dependency-free; transport/ecosystem
> features live in `fastql/integrations/` or behind `pyproject.toml` extras.

## 1. Phase 1 — DataLoader (N+1)

- [x] 1.1 Add `fastql/dataloader.py` with `DataLoader(batch_load_fn, max_batch_size, cache)`: `load`, `load_many`, `clear`, `clear_all`, `prime`.
- [x] 1.2 Implement event-loop batching (pending-batch + `call_soon` dispatch), per-key cache, and key dedup.
- [x] 1.3 Map batch-function per-key errors to the corresponding `load` futures.
- [x] 1.4 Expose request-scoped loader access via `Context`/`Info`; export `DataLoader` from `fastql/__init__.py`.
- [x] 1.5 `tests/test_dataloader.py` covering batching, dedup, `max_batch_size` chunking, cache invalidation, per-key errors, request scoping.

## 2. Phase 1 — Schema extensions / lifecycle hooks

- [x] 2.1 Add `fastql/extensions.py` with `SchemaExtension` (`on_operation/on_parse/on_validate/on_execute`, `resolve`, `get_results`).
- [x] 2.2 Accept `extensions=[...]` on `Schema`/`build_schema`; thread phase hooks through the execution pipeline.
- [x] 2.3 Wrap field resolution with the `resolve` chain (no-op fast path when no extensions); merge `get_results` into `ExecutionResult.extensions`.
- [x] 2.4 Support sync and async hooks (generators/coroutines).
- [x] 2.5 `tests/test_schema_extensions.py` covering phase order, composition, resolver wrapping, async hooks, extensions merge.

## 3. Phase 1 — Subscription execution

- [x] 3.1 Add `subscribe()` in `fastql/execution/` returning an async iterator of `ExecutionResult` or an initial error result.
- [x] 3.2 Resolve the single subscription root field to an async iterator; execute the selection set per yielded value. (Also unwrap `AsyncGenerator/AsyncIterator/AsyncIterable[T]` return hints — real-type and stringized — to the yielded type `T`.)
- [x] 3.3 Enforce single-root-field for subscriptions in `validation/`; isolate per-event resolver errors.
- [x] 3.4 Guarantee source-generator `aclose()` on consumer cancellation/disconnect; export `subscribe` from `fastql/__init__.py`.
- [x] 3.5 `tests/test_subscriptions.py` covering stream-per-event, single-root enforcement, initial errors, per-event error isolation, cleanup.

## 4. Phase 1 — Validation completeness

- [x] 4.1 Add NoFragmentCycles rule to `validation/rules.py`.
- [x] 4.2 Add KnownDirectives + DirectivesInValidLocations rules.
- [x] 4.3 Add PossibleFragmentSpreads rule.
- [x] 4.4 Add LoneAnonymousOperation rule.
- [x] 4.5 Add uniqueness rules (operation names, variable names, argument names, input-object field names).
- [x] 4.6 Add OverlappingFieldsCanBeMerged (correct subset first, with conformance cases).
- [x] 4.7 Extend `tests/test_validation.py` with one case per new rule.

## 5. Phase 1 — Error handling polish

- [x] 5.1 Add `extensions` to `GraphQLError` and include it in `formatted()` only when present.
- [x] 5.2 Add a configurable masking policy to the executor (mask unexpected errors, pass through explicit `GraphQLError`, preserve `original_error`).
- [x] 5.3 `tests/test_execution.py` additions for error extensions and masking behavior.

## 6. Phase 1 — Test client & schema export CLI

- [x] 6.1 Add `fastql/testing.py` with `GraphQLTestClient` (query/mutation `execute` + subscription collection); export it.
- [x] 6.2 Add `export-schema module:attr [--output] [--format sdl|json]` to `fastql/cli.py`.
- [x] 6.3 `tests/test_testing_client.py` and `tests/test_cli.py` additions (SDL to file/stdout, introspection JSON, bad target exits non-zero).

## 7. Phase 2 — Generic types

- [x] 7.1 Accept `Generic[T]`/`TypeVar` on `@Type`/`@Input`/`@Interface`; defer concretization.
- [x] 7.2 Synthesize one concrete type per unique parametrization in `schema_builder.py`; memoize in the registry.
- [x] 7.3 Derive synthetic names (`UserConnection`) with an override hook; resolve `TypeVar` fields against concrete params.
- [x] 7.4 `tests/test_generics.py` covering naming stability, distinct parametrizations, field resolution, name override.

## 8. Phase 2 — Relay pagination

- [x] 8.1 Add `fastql/relay.py`: `Node` interface, global-ID codec, type→resolver registry, root `node(id)` query.
- [x] 8.2 Add generic `Connection[T]`/`Edge[T]`/`PageInfo` and a cursor-slicing helper.
- [x] 8.3 Wire `first/after`/`last/before` arguments and page-info flags.
- [x] 8.4 `tests/test_relay.py` covering node resolution, global-id round-trip, connection shape, forward/backward pagination.

## 9. Phase 2 — Custom directives, field visibility, enum customization

- [x] 9.1 Add `@Directive` authoring (name, `locations`, args from hints, repeatable, description) registering `DirectiveDefinition`.
- [x] 9.2 Validate applied-directive locations and argument coercion at build time; render applied directives in `sdl.py`.
- [x] 9.3 Add private (schema-excluded) and external (federation) field markers in the decorators/IR and SDL printer.
- [x] 9.4 Add per-member enum customization (name/description/deprecation) to `@Enum`.
- [x] 9.5 `tests/test_directives.py`, `tests/test_field_visibility.py`, and `test_type_system.py` additions for enum customization.

## 10. Phase 3 — Apollo Federation v2

- [x] 10.1 Add `fastql/federation/` with federation directives (`@key/@external/@shareable/@requires/@provides/@inaccessible/@override/@tag`) as applied-directive metadata.
- [x] 10.2 Add a federated-SDL printer with the `@link` import header.
- [x] 10.3 Add `_service { sdl }`, the `_Any`/`_Entity`/`_Service` types, and `_entities(representations)` with a per-type reference-resolver registry.
- [x] 10.4 `tests/test_federation.py` covering directive rendering, `_service`, ordered `_entities` resolution, reference resolvers.

## 11. Phase 3 — Subscription transport (integrations)

- [ ] 11.1 Add a `graphql-transport-ws` WebSocket handler in `fastql/integrations/` driving `subscribe()`.
- [ ] 11.2 Add an SSE (`text/event-stream`) transport for subscriptions/incremental results.
- [ ] 11.3 Add `multipart/mixed` streaming for streaming-capable adapters; wire transports into ASGI/Starlette/FastAPI adapters.
- [ ] 11.4 `tests/test_subscription_transport.py` covering connection_ack→next→complete, error message, client complete, SSE streaming.

## 12. Phase 3 — File uploads & query batching (HTTP)

- [ ] 12.1 Add an `Upload` scalar usable as an input type.
- [ ] 12.2 Parse `multipart/form-data` per graphql-multipart-request-spec (operations/map/files) in the shared HTTP handler; reject malformed maps.
- [ ] 12.3 Accept JSON-array batch bodies (configurable, bounded); return aligned result arrays with isolated per-op errors.
- [ ] 12.4 `tests/test_uploads.py` and `tests/test_query_batching.py` (single/multiple files, malformed map, array response, disabled/oversized rejection).

## 13. Phase 3 — Tracing / instrumentation

- [ ] 13.1 Add an Apollo-style tracing extension merging timing into `ExecutionResult.extensions`.
- [ ] 13.2 Add an OpenTelemetry extension (behind `[opentelemetry]` extra, lazy import) emitting operation/field spans.
- [ ] 13.3 Add the `opentelemetry` extra to `pyproject.toml`; import-guard test that core works without it.
- [ ] 13.4 `tests/test_tracing.py` covering tracing block presence and OTel no-op without the dependency.

## 14. Phase 4 — Pydantic integration

- [ ] 14.1 Add `[pydantic]` extra and a lazy-imported integration deriving output/input types from Pydantic models.
- [ ] 14.2 Construct + validate Pydantic models from coerced inputs; surface validation failures as GraphQL errors.
- [ ] 14.3 `tests/test_pydantic.py` covering type/input generation, validation error surfacing, and core-without-pydantic import guard.

## 15. Phase 4 — Incremental delivery (@defer/@stream)

- [ ] 15.1 Parse/validate `@defer` (fragments) and `@stream` (list fields, `initialCount`).
- [ ] 15.2 Produce initial + incremental payloads in the executor; collapse to a single result over non-streaming transports.
- [ ] 15.3 Wire incremental payloads over the multipart/SSE transports from Phase 3.
- [ ] 15.4 `tests/test_incremental_delivery.py` covering deferred fragment, `@defer(if:false)` inline, streamed list, non-streaming collapse.

## 16. Phase 4 — Additional framework adapters

- [ ] 16.1 Add AIOHTTP, Sanic, Litestar, Quart, and Django Channels adapters delegating to the shared HTTP/subscription handlers.
- [ ] 16.2 Add corresponding extras to `pyproject.toml` with isolated imports.
- [ ] 16.3 `tests/test_framework_integrations.py` additions per new adapter (GET/POST, JSON shape, GraphiQL).

## 17. Docs & finalization

- [ ] 17.1 Add docs pages under `docs/` for each new capability and update the capability catalog.
- [ ] 17.2 Update `README.md` feature list and `CHANGELOG.md`.
- [ ] 17.3 Run full `pytest`; ensure base install stays dependency-free (import-guard tests green).
