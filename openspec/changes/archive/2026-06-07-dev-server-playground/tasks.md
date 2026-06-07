## 1. Minimal async HTTP core (capability: dev-server)

- [x] 1.1 Create `fastql/server.py` with an `asyncio.start_server` listener and a connection handler
- [x] 1.2 Implement a minimal HTTP/1.1 request parser: request line, headers, and `Content-Length` body
- [x] 1.3 Implement a response writer (status line, headers, body) responding with `Connection: close`
- [x] 1.4 Implement a router dispatching by method + path, and `serve(schema, host="127.0.0.1", port=7691, path="/graphql")`
- [x] 1.5 Add the startup banner (base URL + routes) and `KeyboardInterrupt` graceful shutdown
- [x] 1.6 Tests: server binds to default `127.0.0.1:7691` and to a custom host/port; clean shutdown

## 2. GraphQL HTTP endpoint (capability: dev-server)

- [x] 2.1 Handle `POST {path}`: parse JSON `{query, variables, operationName}` and `await execute(schema, ...)`
- [x] 2.2 Handle `GET {path}?query=...&variables=...&operationName=...`
- [x] 2.3 Serialize the `ExecutionResult` to an `application/json` `{data, errors}` body
- [x] 2.4 Map transport errors to status codes: malformed JSON → `400`, unknown path → `404`, bad method → `405`; keep GraphQL errors at `200`
- [x] 2.5 Add minimal permissive CORS headers for browser convenience
- [x] 2.6 Tests: POST query returns `{data}`; GET query works; variables/operationName forwarded; `400`/`404`/`405`; validation error stays `200` with `errors`

## 3. GraphiQL playground (capability: graphql-playground)

- [x] 3.1 Create `fastql/playground.py`: a function returning the GraphiQL HTML page (CDN assets) parameterized by the GraphQL endpoint path
- [x] 3.2 Serve the playground HTML at `GET /` with `text/html`
- [x] 3.3 Tests: `GET /` returns `200` HTML containing the GraphiQL bootstrap and the (default and custom) endpoint path

## 4. Schema endpoints (capability: schema-endpoints)

- [x] 4.1 Create `fastql/sdl.py`: `print_schema(schema)` rendering the type-system IR to SDL (types, fields, args, defaults, enums, unions, interfaces, scalars, `@deprecated`)
- [x] 4.2 Serve `GET /schema.graphql` as `text/plain` using `print_schema`
- [x] 4.3 Serve `GET /schema.json` by executing the standard introspection query via `execute` and returning its `data` as JSON
- [x] 4.4 Tests: `print_schema` output contains `type Query` and renders a `@deprecated` field; `/schema.graphql` returns SDL; `/schema.json` returns a `__schema` JSON object

## 5. CLI (capability: server-cli)

- [x] 5.1 Create `fastql/cli.py`: argument parsing for `serve <target>` with `--host` and `--port` flags
- [x] 5.2 Implement dotted-path import of the schema object (`module:attr` and `module.attr`); exit non-zero with a clear message on failure
- [x] 5.3 Create `fastql/__main__.py` dispatching `python -m fastql` to the CLI
- [x] 5.4 Wire the CLI to `serve(...)`; ensure Ctrl-C exits cleanly with a shutdown message
- [x] 5.5 Tests: dotted-path import resolves a schema; host/port overrides applied; invalid target exits non-zero

## 6. Public API, boundary, and end-to-end

- [x] 6.1 Export `serve` (and `print_schema`) from `fastql/__init__.py`
- [x] 6.2 Confirm no new runtime dependency is added to `pyproject.toml` (stdlib only)
- [x] 6.3 Add a boundary test asserting the core package does not import `fastql.server`
- [x] 6.4 Add an `examples/hello.py` sample schema and an integration test that boots `serve()` on an ephemeral port and asserts `POST /graphql`, `GET /`, `GET /schema.graphql`, and `GET /schema.json`
- [x] 6.5 Add a README/quickstart section showing `python -m fastql serve examples.hello:schema` and the default port 7691
- [x] 6.6 Run the full `pytest` suite and confirm all dev-server scenarios pass
