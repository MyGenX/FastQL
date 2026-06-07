## Why

FastQL can execute GraphQL operations but does not yet provide production-oriented integration points for the Python web frameworks applications already use. A shared integration model is needed now so FastAPI, Django, Flask, Starlette, generic ASGI, and future adapters behave consistently without forcing unrelated framework dependencies into every installation.

## What Changes

- Introduce a framework-neutral HTTP transport contract that normalizes GraphQL request parsing, execution, error formatting, headers, context creation, and optional GraphiQL/schema endpoints.
- Add first-class adapters for generic ASGI, Starlette, FastAPI, Flask, and Django, each using framework-native application, routing, request, response, and lifecycle conventions.
- Provide a consistent FastQL integration API across frameworks while preserving framework-specific extension points such as FastAPI dependencies, Django URL views, Flask blueprints/views, Starlette routes, and direct ASGI mounting.
- Extend request context creation so adapters can expose the native request, response hooks, application state, and user-defined values to resolvers without coupling the core executor to a web framework.
- Add independent packaging extras such as `fastql[asgi]`, `fastql[starlette]`, `fastql[fastapi]`, `fastql[flask]`, and `fastql[django]`, plus a documented aggregate extra, while keeping `pip install fastql` free of web-framework runtime dependencies.
- Add adapter contract tests, framework-specific integration tests, packaging metadata tests, examples, and documentation covering installation and mounting patterns.
- Establish an extension contract for future integrations without committing to additional adapters in this change.

## Capabilities

### New Capabilities

- `http-integration-contract`: Shared request, response, execution, context, endpoint, and error behavior used by every web-framework adapter.
- `python-web-framework-adapters`: Framework-native ASGI, Starlette, FastAPI, Flask, and Django adapters with a consistent FastQL-facing API.
- `integration-packaging`: Independent optional-dependency extras, import boundaries, compatibility policy, and installation validation for framework integrations.

### Modified Capabilities

- `context-injection`: Define how framework-native request data and user context factories are composed into the execution context for each request.
- `schema-endpoints`: Make GraphQL, GraphiQL, SDL, and introspection endpoint behavior reusable and configurable across production framework adapters.

## Impact

- New integration modules under `fastql/integrations/` and shared transport code that consumes the existing `execute`, `print_schema`, introspection, and playground APIs.
- Changes to `pyproject.toml` optional dependencies and test dependencies, without adding mandatory runtime dependencies to the core package.
- New public imports for adapter factories/classes and shared request-context types.
- New tests that install or exercise supported framework versions and verify equivalent behavior across synchronous WSGI-style and asynchronous ASGI-style adapters.
- Documentation and examples for framework-specific setup, configuration, context access, and deployment.

## Non-goals

- Replacing framework routers, middleware, authentication, dependency injection, or deployment servers.
- Moving HTTP or framework-specific types into the GraphQL execution engine.
- Supporting subscriptions or WebSocket protocols in the initial adapter release; the design will leave a compatible extension point for them.
- Shipping adapters beyond ASGI, Starlette, FastAPI, Flask, and Django in this change.
