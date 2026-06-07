# Changelog

## Unreleased

### Added

- A shared dependency-free GraphQL-over-HTTP handler and request-aware `HTTPContext`.
- Generic ASGI, Starlette, FastAPI, Flask, and Django integrations.
- Independent `asgi`, `starlette`, `fastapi`, `flask`, and `django` installation extras, plus `all`.
- Configurable GraphiQL, SDL, and introspection routes for production adapters.

### Deferred

- WebSocket subscriptions, multipart uploads, batching, persisted queries, and incremental delivery remain outside the initial integration contract.
