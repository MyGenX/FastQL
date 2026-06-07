## 1. Public Integration API and Module Boundaries

- [x] 1.1 Define the public adapter names, shared option names, import paths, and `fastql/integrations/` module layout for HTTP, ASGI, Starlette, FastAPI, Flask, and Django integrations.
- [x] 1.2 Add dependency-free normalized HTTP request/response models, endpoint configuration, and response controls without importing optional frameworks from `fastql` or `fastql.integrations`.
- [x] 1.3 Add `HTTPContext` and the sync/async context-factory contract, including enrichment, replacement, request state, application access, and per-request response headers.
- [x] 1.4 Add pytest coverage for shared model validation, context factory behavior, response-control isolation, and framework-free imports.

## 2. Shared GraphQL-over-HTTP Handler

- [x] 2.1 Implement GET query-parameter and POST JSON payload parsing for `query`, `variables`, `operationName`, and `extensions`, including supported media-type and field-type validation.
- [x] 2.2 Implement method enforcement, GET operation safety, content negotiation, structured transport errors, and stable GraphQL result status behavior.
- [x] 2.3 Implement configurable GraphiQL, SDL, and introspection JSON handling as shared services independent of the development server dispatcher.
- [x] 2.4 Apply context factories, root values, execution options, and response controls around calls to the existing FastQL executor.
- [x] 2.5 Add protocol contract tests covering valid GET/POST execution, malformed JSON, unsupported media types and methods, GET mutations, operation selection, resolver errors, content negotiation, and disabled routes.
- [x] 2.6 Refactor the built-in development server to reuse compatible shared handler behavior while preserving its documented CLI and endpoint behavior, then run its regression tests.

## 3. Generic ASGI Reference Adapter

- [x] 3.1 Implement the dependency-free ASGI 3 application, including HTTP scope validation, request-body collection, normalized request conversion, response start/body messages, and mounting path behavior.
- [x] 3.2 Expose native ASGI scope, receive/send data, application state, and response controls through the request context without coupling the executor to ASGI.
- [x] 3.3 Handle unsupported scopes and disconnected requests according to ASGI conventions without attempting GraphQL execution.
- [x] 3.4 Add pytest coverage using an in-process ASGI harness for direct and mounted execution, companion endpoints, context access, response headers, malformed requests, and unsupported scopes.

## 4. Starlette and FastAPI Adapters

- [x] 4.1 Implement a Starlette-native router or route factory that converts Starlette requests and responses and composes correctly with mounts and middleware.
- [x] 4.2 Implement an `APIRouter`-compatible FastAPI adapter with router dependencies, tags, URL prefixes, and OpenAPI inclusion controls.
- [x] 4.3 Ensure both adapters use the shared configuration and handler while exposing their native request objects through `HTTPContext`.
- [x] 4.4 Add Starlette integration tests for route registration, mounted prefixes, middleware state, GraphiQL/schema routes, response controls, and shared protocol conformance.
- [x] 4.5 Add FastAPI integration tests for router inclusion, dependencies, tags/OpenAPI controls, request context, enabled routes, and shared protocol conformance.

## 5. Flask and Django Adapters

- [x] 5.1 Implement and test one internal synchronous bridge for awaiting the shared handler from synchronous framework boundaries without nesting a running event loop.
- [x] 5.2 Implement a Flask `Blueprint` factory with stable endpoint names, URL-prefix composition, native request/response conversion, and application-context access.
- [x] 5.3 Add Flask integration tests for blueprint registration, prefixes, hooks or decorators, request context, response controls, async resolvers, and shared protocol conformance.
- [x] 5.4 Implement an async-capable Django class-based view and URL-pattern helper with native request/response conversion, middleware compatibility, and explicit configurable CSRF exemption.
- [x] 5.5 Add Django integration tests for URL inclusion, middleware and request user access, secure default CSRF behavior, opt-in exemption, async execution, and shared protocol conformance.

## 6. Optional Dependency Packaging

- [x] 6.1 Select and document supported framework version ranges compatible with Python 3.11+, then add independent `asgi`, `starlette`, `fastapi`, `flask`, and `django` extras plus an `all` aggregate extra to `pyproject.toml`.
- [x] 6.2 Add lazy optional-dependency checks so importing a missing adapter reports the exact `fastql[framework]` installation command while unrelated adapters and core imports remain usable.
- [x] 6.3 Add packaging tests that build and inspect wheel metadata, verify the base install has no framework dependency, and verify each extra excludes unrelated top-level frameworks.
- [x] 6.4 Add isolated-environment import smoke tests for the base package, every individual extra, and the aggregate extra.
- [x] 6.5 Configure CI or tox/nox coverage for representative supported versions of Starlette, FastAPI, Flask, and Django and run the adapter conformance suite across that matrix.

## 7. Documentation and Examples

- [x] 7.1 Add an integration overview explaining the shared FastQL model, choosing an adapter, base versus extra installation, and the supported-version policy.
- [x] 7.2 Add runnable generic ASGI, Starlette, FastAPI, Flask, and Django examples using framework-native mounting patterns and the same schema and context concepts.
- [x] 7.3 Document `HTTPContext`, custom typed context subclasses, sync/async factories, middleware-provided state, response headers, and framework-owned security policy.
- [x] 7.4 Document GraphQL-over-HTTP support and exclusions, GraphiQL/schema endpoint configuration, Django CSRF configuration, and the future adapter extension contract.
- [x] 7.5 Add documentation tests that verify installation commands, public imports, example syntax, navigation entries, and internal links.

## 8. Release Verification

- [x] 8.1 Run formatting and static checks required by the repository and resolve issues in integration modules, examples, and tests.
- [x] 8.2 Run the full pytest suite, every framework adapter conformance suite, and documentation validation with no regressions to core execution or the development server.
- [x] 8.3 Build the source distribution and wheel, inspect included integration modules and optional metadata, and smoke-test installation from the built wheel.
- [x] 8.4 Validate the completed OpenSpec change strictly and record the final supported adapters, extras, and known deferred protocol features in release notes.
