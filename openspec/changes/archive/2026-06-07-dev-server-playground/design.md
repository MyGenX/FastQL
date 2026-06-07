## Context

FastQL's core (`graphql-core-framework`) exposes only `build_schema()` and async `execute()` and
deliberately contains no HTTP/transport so it stays web-framework agnostic. The cost is discoverability:
there's no zero-effort way to open a schema in a browser and explore it. This change adds an optional,
built-in **dev server** that sits *above* the core and turns a schema into a locally browsable GraphQL
IDE. It is a developer convenience, not a production transport and not a framework adapter.

Constraints:
- **Zero new runtime dependencies** — stdlib only, mirroring the core's hand-built ethos.
- **Async-native** — the core's `execute` is async, so the server should `await` it directly.
- **Agnostic boundary preserved** — the core must never import the server; the dependency points one way.
- **Minimal** — a dev tool, not hardened infrastructure.

## Goals / Non-Goals

**Goals:**
- `fastql.serve(schema, host="127.0.0.1", port=7691, path="/graphql")` boots a working GraphQL server.
- A browser GraphiQL IDE at `/`, plus SDL (`/schema.graphql`) and introspection JSON (`/schema.json`).
- A CLI (`python -m fastql serve module:attr`) for terminal use.
- No dependencies added; the core remains untouched and unaware of the server.

**Non-Goals:**
- Production hardening, HTTPS/TLS, auth, rate limiting, keep-alive/HTTP-2, chunked transfer.
- Subscriptions/WebSocket, file uploads, persisted queries, hot-reload.
- Any FastAPI/Django/Flask/ASGI adapter (separate future changes).

## Decisions

### D1. A separate `fastql.server` module set, not part of the core
The server lives in `fastql/server.py`, `playground.py`, `sdl.py`, `cli.py`, `__main__.py`, and only
`serve` is added to the public `__init__`. The dependency arrows point from the server to the core, never
back. **Alternative:** baking HTTP into the core — rejected outright; it would break the agnostic
guarantee that the whole framework is built around.

### D2. Minimal HTTP over `asyncio.start_server` (no third-party server)
We hand-roll an HTTP/1.1 request parser (request line + headers + `Content-Length` body) on top of
`asyncio.start_server`, respond with `Connection: close`, and skip chunked encoding and keep-alive. This
adds zero dependencies and `await`s `execute` naturally. **Alternatives considered:**
- `http.server.BaseHTTPRequestHandler` (sync) — would force bridging sync handlers to the async executor
  via `asyncio.run`/thread offload per request; clumsier than a native async server.
- ASGI + uvicorn — more production-like but adds a real dependency and overlaps with the future ASGI
  adapter change. Rejected for a *minimal* dev server.
**Trade-off accepted:** our parser handles only the narrow subset a dev tool needs; that's acceptable and
explicitly documented as non-production.

### D3. GraphiQL loaded from a CDN
`playground.py` returns a small HTML page that pulls GraphiQL's JS/CSS from a CDN and points its fetcher
at the configured GraphQL `path`. **Alternatives:** vendoring GraphiQL assets for offline use (larger
repo, assets to maintain) or Apollo Sandbox (also CDN). CDN GraphiQL is the smallest, most standard
option; the trade-off is that the playground needs internet at runtime — acceptable for a dev tool, and
the SDL/introspection endpoints still work offline.

### D4. SDL via a new `print_schema` utility
To "show the schema" directly we add `sdl.print_schema(schema)` that walks the core's type-system IR and
emits canonical SDL (types, fields, args, defaults, enum/union/interface/scalar, `@deprecated`). This is
small, self-contained, and complements the introspection JSON endpoint (which reuses the core's
introspection capability through `execute`). **Alternative:** deriving SDL from the introspection result —
more indirection; printing the IR directly is simpler and clearer.

### D5. CLI imports the schema by dotted path
`python -m fastql serve module:attr` (also `module.attr`) imports the named object and calls `serve`,
with `--host`/`--port` overrides. On import failure or a missing attribute it exits non-zero with a clear
message. `__main__.py` dispatches to `cli.py`. **Alternative:** a config file — unnecessary for a minimal
tool; a dotted path is the least-friction entry.

### Routing & error model
A single async handler parses the request, then routes by method + path:
`POST|GET {path}` → execute; `GET /` → GraphiQL; `GET /schema.graphql` → SDL; `GET /schema.json` →
introspection. Transport errors map to status codes (`400` malformed JSON, `404` unknown path, `405` bad
method); GraphQL-level errors return `200` with an `errors` array per the GraphQL-over-HTTP convention.
The loop catches `KeyboardInterrupt` for a clean shutdown banner.

## Risks / Trade-offs

- **Hand-rolled HTTP parser misses edge cases** → Scope it to the dev-tool subset (Content-Length bodies,
  no chunked/keep-alive), document it as non-production, and cover the real routes with integration tests.
- **CDN GraphiQL needs internet** → Acceptable for a dev tool; SDL and introspection endpoints work
  offline, and a vendored-offline option can be added later if requested.
- **Accidental coupling of core → server** → Enforce with an explicit test asserting the core package does
  not import `fastql.server`, and keep `serve` the only server symbol exported from `__init__`.
- **`print_schema` drifting from the core IR** → Build it directly against the documented IR and test its
  output against a representative schema (objects, args, enums, unions, deprecations).
- **Binding to `0.0.0.0` exposes the dev server** → Default to `127.0.0.1`; exposing externally is an
  explicit opt-in via `--host`, and docs note it's a dev tool without auth/TLS.

## Migration Plan

Purely additive: new modules plus a `serve` export. No existing behavior changes and the core is
untouched, so there is nothing to migrate; rollback means removing the new modules. This change depends on
the `graphql-core-framework` change being implemented first (it consumes `execute`, `build_schema`, and
introspection); until then it is planned against that public API.

## Open Questions

- Exact CDN/version pin for GraphiQL assets (and whether to add a vendored-offline fallback later).
- Whether to add a tiny landing page linking the routes, or keep `GET /` as GraphiQL directly (leaning
  GraphiQL directly for minimalism).
- Whether `--host 0.0.0.0` should print an explicit "exposed without auth" warning (leaning yes).
