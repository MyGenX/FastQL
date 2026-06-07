## Why

FastQL's core is deliberately web-framework agnostic and ships **no HTTP/transport** — it only exposes
`build_schema()` and async `execute()`. That makes a schema hard to *try out*: there is no way to point
a browser at it, run queries, or see the schema without writing server glue or pulling in FastAPI/Django.
This change adds an **optional, built-in minimal dev server** so a developer can run their schema locally
on a default port and explore it in a browser GraphQL IDE — instantly, with zero new dependencies. It is
a developer convenience that lives *above* the core and consumes its public API; the agnostic core stays
untouched.

## What Changes

- Add a new `fastql.server` module set (server, playground, SDL printer, CLI) that depends only on the
  Python standard library — **no new runtime dependencies**.
- Add `fastql.serve(schema, host="127.0.0.1", port=7691, path="/graphql")`: an `asyncio`-based minimal
  HTTP/1.1 server that awaits the core's async `execute`.
- Default to port **7691** ("fgql" mnemonic) and host `127.0.0.1`, both overridable.
- Expose routes:
  - `POST /graphql` (and `GET /graphql?query=...`) — execute a GraphQL request, return `{data, errors}` JSON.
  - `GET /` — serve a **GraphiQL** IDE page (loaded from CDN) wired to the GraphQL endpoint.
  - `GET /schema.graphql` — the schema as **SDL** text (via a new `print_schema` utility).
  - `GET /schema.json` — the schema as an **introspection** JSON result.
- Return proper error responses: malformed JSON → `400`, unknown path → `404`, wrong method → `405`.
- Add a **CLI**: `python -m fastql serve module:attr [--host H] [--port P]`, importing the schema by
  dotted path, printing a startup banner, and shutting down gracefully on Ctrl-C.
- Export `serve` from the package's public API.
- Non-goals (explicit): not a production server, not a FastAPI/Django/Flask/ASGI adapter; no HTTPS/TLS,
  authentication, subscriptions/WebSocket, file uploads, or hot-reload.

## Capabilities

### New Capabilities
- `dev-server`: The `serve()` function and `asyncio` HTTP handling — the GraphQL POST/GET endpoint, JSON request/response, default port 7691, host/path configuration, and error responses.
- `graphql-playground`: Serving the GraphiQL in-browser IDE at `GET /`, wired to the GraphQL endpoint.
- `schema-endpoints`: `GET /schema.graphql` (SDL via `print_schema`) and `GET /schema.json` (introspection JSON).
- `server-cli`: `python -m fastql serve module:attr` with host/port flags, dotted-path schema import, banner, and graceful shutdown.

### Modified Capabilities
<!-- None — the agnostic core is unchanged; this change consumes its existing public API. -->

## Impact

- **New code**: `fastql/server.py`, `fastql/playground.py`, `fastql/sdl.py`, `fastql/cli.py`,
  `fastql/__main__.py`, and a `serve` export in `fastql/__init__.py`.
- **Dependencies**: none added — stdlib only (`asyncio`, plus `http.client`/`urllib` in tests).
- **Depends on the core's public API**: `execute`, `Schema`/`build_schema`, and the introspection
  capability; `print_schema` reads the core's type-system IR. No core changes required.
- **Boundary invariant**: the core package must not import `fastql.server`, preserving the
  framework-agnostic core; production transport adapters remain separate future changes.
- **Tests**: integration tests that boot the server on an ephemeral port and exercise each route.
