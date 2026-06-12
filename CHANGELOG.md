# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-06-12

### Added

- Optional Pydantic integration deriving GraphQL output/input types from Pydantic
  models, with validation surfaced as GraphQL errors (`[pydantic]` extra).
- Incremental delivery: `@defer` (fragments) and `@stream` (list fields) via
  `execute_incremental()`, collapsing to a single result on non-streaming transports.
- Additional framework adapters — AIOHTTP, Sanic, Litestar, Quart, and Django
  Channels — with isolated `aiohttp`, `sanic`, `litestar`, `quart`, and `channels`
  extras, each delegating to the shared HTTP/subscription handlers.

### Changed

- Expanded the documentation site with a per-capability "Advanced capabilities"
  section and a capability catalog mapping every feature to its canonical spec.

### Fixed

- Introspection now serializes `defaultValue` as a GraphQL literal, fixing the
  GraphiQL "Error fetching schema" failure on the `@deprecated` reason default.
- `fastql.__version__` is derived from the installed package metadata so it stays in
  sync with `pyproject.toml`.

## [1.0.0] - 2026-06-11

First stable release.

### Added

- A shared dependency-free GraphQL-over-HTTP handler and request-aware `HTTPContext`,
  with generic ASGI, Starlette, FastAPI, Flask, and Django integrations behind
  isolated `asgi`, `starlette`, `fastapi`, `flask`, and `django` extras (plus `all`).
- Configurable GraphiQL, SDL, and introspection routes for production adapters.
- Streaming subscription transports: `graphql-transport-ws` (WebSocket), Server-Sent
  Events, and `multipart/mixed`.
- Apollo Federation v2: federation directives, federated SDL, `_service` / `_entities`,
  and reference resolvers.
- `Upload` scalar with `multipart/form-data` parsing, and bounded JSON-array query
  batching.
- Apollo-style tracing and an optional OpenTelemetry extension (`[opentelemetry]` extra).
- Expanded query validation (fragment cycles, known/located directives, possible
  fragment spreads, lone anonymous operation, uniqueness, and
  overlapping-fields-can-be-merged) and configurable error masking.
- A Mintlify documentation site.

## [0.0.2] - 2026-06-09

### Added

- Generic types (`Generic[T]`) concretized per unique parametrization.
- Relay pagination: the `Node` interface, global-ID codec, and cursor
  `Connection` / `Edge` / `PageInfo` types.
- Custom directive authoring (`@Directive`), private/external field markers, and
  per-member enum customization (`enum_value`).

## [0.0.1] - 2026-06-08

### Added

- Initial release of the hand-built GraphQL engine (lexer → parser → validator →
  executor) with the unified decorator schema API, dependency injection / context
  layer, introspection, and SDL output — zero runtime dependencies, Python 3.11+.
- `DataLoader` for request-scoped batching and caching, `SchemaExtension` lifecycle
  hooks with per-field `resolve` wrapping, and subscription execution (`subscribe()`).
- `GraphQLTestClient` and an `export-schema` CLI (SDL / introspection JSON).
- A built-in development server and browser playground.

[Unreleased]: https://github.com/MyGenX/FastQL/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/MyGenX/FastQL/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/MyGenX/FastQL/compare/v0.0.2...v1.0.0
[0.0.2]: https://github.com/MyGenX/FastQL/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/MyGenX/FastQL/releases/tag/v0.0.1
