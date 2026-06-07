## Context

FastQL has an async executor, schema printing, introspection, GraphiQL rendering, and a dependency-free development HTTP server. Production applications, however, already have a web framework that owns routing, middleware, request lifecycle, authentication, and deployment. Implementing GraphQL parsing and execution separately in every adapter would create behavioral drift, while importing frameworks from the core package would violate FastQL's zero-dependency and framework-agnostic boundaries.

The integration surface must cover both ASGI-style async frameworks and WSGI-style synchronous frameworks. It must also feel native in each ecosystem without forcing users to relearn configuration names and context behavior for every framework.

## Goals / Non-Goals

**Goals:**

- Define one testable GraphQL-over-HTTP handler used by all adapters.
- Ship first-class generic ASGI, Starlette, FastAPI, Flask, and Django integrations.
- Preserve framework-native routing, middleware, request objects, and extension mechanisms.
- Use consistent configuration for schema, path, GraphiQL, schema endpoints, root values, context creation, and execution options.
- Keep `fastql` dependency-free and isolate framework imports behind optional extras.
- Make future adapters implement a small documented request/response conversion contract.

**Non-Goals:**

- Implement GraphQL subscriptions, WebSocket protocols, multipart uploads, request batching, persisted queries, or incremental delivery.
- Replace framework authentication, authorization, CORS, CSRF, sessions, middleware, or server deployment.
- Turn the built-in development server into a production server.
- Split integrations into separately versioned Python distributions in this change.

## Decisions

### 1. Add a framework-neutral async HTTP handler

Create `fastql.integrations.http` with dependency-free request and response value objects, endpoint configuration, response controls, and an async `GraphQLHTTPHandler`. The handler will normalize GET and JSON POST requests, validate transport inputs, enforce operation rules, call `execute`, format results, render GraphiQL and schema documents when enabled, and return a framework-neutral response.

Adapters will only translate native requests into the normalized request, invoke the handler, and translate its response back into a native response. Contract tests will run once against the handler and again as a smaller conformance suite against every adapter.

Alternative considered: implement the full flow independently in each framework. This gives maximal framework control but multiplies parsing, status, error, and endpoint behavior, making consistency and maintenance substantially harder.

### 2. Follow a conservative GraphQL-over-HTTP subset

The initial handler will support GET query parameters and POST JSON bodies containing `query`, `variables`, `operationName`, and optional `extensions`. It will accept `application/json` and `application/graphql-response+json`, reject unsupported media types, reject mutations and subscriptions over GET, and return JSON GraphQL results using explicit HTTP status rules. Transport failures use appropriate 4xx responses; successfully parsed GraphQL operations, including validation and resolver errors, return a formatted GraphQL result.

GraphiQL will be served from the configured GraphQL path only when enabled, a GET request does not provide a query, and the client accepts HTML. SDL and introspection document routes remain independently configurable.

Alternative considered: support every draft GraphQL-over-HTTP feature immediately. Multipart forms, batching, and streaming introduce separate execution and security concerns and are deferred until their contracts are specified.

### 3. Use shared configuration with framework-native adapter objects

All integrations will accept the same core options: `schema`, `path`, `context_factory`, `root_value`, `graphiql`, `schema_path`, `introspection_path`, and execution options. The exported adapter shape will remain native:

- Generic ASGI: an ASGI 3 callable application suitable for direct use or mounting.
- Starlette: a router or route factory using Starlette `Request` and `Response` objects.
- FastAPI: an `APIRouter`-compatible integration that supports router dependencies and OpenAPI inclusion controls.
- Flask: a `Blueprint` factory with configurable endpoint names and URL prefix behavior.
- Django: an async-capable class-based view plus a URL-pattern helper.

The modules will use predictable public names and export a short framework-specific mounting example. The shared option names and behavior are the FastQL style; the returned objects and registration flow are the framework style.

Alternative considered: expose an identical `create_app()` function in every module. That is superficially uniform but obscures native concepts such as FastAPI routers, Flask blueprints, and Django views.

### 4. Introduce a request-aware context envelope

Add a dependency-free `HTTPContext` derived from `Context`, containing the native request, application object when available, mutable request state, and a `ResponseControl` for adding response headers. Before execution, each adapter constructs this envelope and calls the optional context factory with it. Factories may be synchronous or asynchronous and may enrich and return the envelope or return a replacement context object.

The object returned by the factory becomes `Info.context` and the value injected into `Context` parameters. Returning a replacement is an explicit opt-out from the standard envelope, so applications that need both custom typing and native request access should subclass `HTTPContext`.

Alternative considered: pass only the framework request to the factory. That makes simple cases easy but gives no portable place for app state or response controls and causes every adapter to invent a different factory contract.

### 5. Keep optional dependencies isolated by module and extra

The wheel remains a single `fastql` distribution. `pyproject.toml` will define independent extras for `asgi`, `starlette`, `fastapi`, `flask`, and `django`, plus `all` as their union. The generic ASGI adapter has no third-party requirement, so its extra may be empty but remains a documented installation target for symmetry. Framework modules import their framework only when that module is imported and raise an actionable error naming the required extra if it is unavailable. Importing `fastql` or `fastql.integrations` must never import an optional framework.

Alternative considered: publish packages such as `fastql-fastapi`. Separate distributions provide stronger dependency isolation but add release coordination, version compatibility, and discovery overhead before the adapter API has stabilized.

### 6. Bridge synchronous frameworks at the adapter boundary

The shared handler remains async because FastQL execution is async-first. ASGI, Starlette, FastAPI, and async Django views await it directly. Flask and any synchronous Django entry point use one internal sync bridge that executes the coroutine without changing executor behavior. The bridge must work when no event loop is present and avoid attempting to nest an already-running loop.

Alternative considered: create a synchronous executor path. Maintaining two execution engines would add risk and is unnecessary for adapting a request boundary.

### 7. Leave security and middleware policy with the host framework

Adapters will not inject permissive CORS headers or bypass authentication middleware. FastAPI dependencies, Starlette middleware, Flask decorators/hooks, and Django middleware continue to run normally. Django CSRF behavior will be explicit and secure by default, with an opt-in documented exemption for API deployments that use other protections. Unexpected internal exceptions are converted to a generic GraphQL/HTTP error unless framework debug mode explicitly allows its normal exception path.

Alternative considered: copy the development server's permissive CORS behavior. Production policy cannot be selected safely without application context.

## Risks / Trade-offs

- [Framework APIs and supported versions diverge] -> Define tested version ranges in optional dependencies, run a compatibility matrix, and keep adapter code isolated per framework.
- [Shared behavior can hide useful native features] -> Keep conversion hooks and framework-native registration objects, and avoid wrapping middleware or dependency systems.
- [Sync bridging adds latency and thread overhead] -> Keep the executor async-first, document async Django as preferred, and constrain bridging to synchronous request boundaries.
- [Optional imports can accidentally leak into the base install] -> Add clean-environment import and wheel-metadata tests for every extra.
- [HTTP semantics can drift from the GraphQL-over-HTTP specification] -> Centralize protocol behavior and encode each supported rule in handler contract tests.
- [Context replacement can remove standard request access] -> Document replacement semantics and make subclassing `HTTPContext` the recommended typed customization path.

## Migration Plan

1. Extract reusable endpoint and request handling behavior without changing the existing development server's public API.
2. Add the shared context envelope and HTTP handler behind new integration modules.
3. Implement and test the generic ASGI adapter first as the async reference adapter.
4. Add Starlette and FastAPI adapters, then Flask and Django adapters using the same conformance suite.
5. Add optional extras, isolated-import tests, framework examples, and documentation.
6. Keep the existing `fastql serve` command operational; it may delegate to shared handler code when behavior remains compatible.

Rollback consists of removing the new integration modules and extras. Existing schema, execution, and development-server APIs remain backward compatible.

## Open Questions

- Exact minimum framework versions will be selected during implementation from versions that support Python 3.11 and the native APIs used by the adapters, then locked into the test matrix and documented compatibility table.
- Public adapter class and factory names should be finalized during the first implementation task and then treated as stable across all examples and documentation.
