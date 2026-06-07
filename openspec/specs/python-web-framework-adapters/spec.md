# python-web-framework-adapters Specification

## Purpose
First-party FastQL adapters for common Python web frameworks (generic ASGI, Starlette, FastAPI, Flask, Django) that expose the shared FastQL execution behavior through framework-native registration objects with consistent configuration and a documented extension contract.

## Requirements
### Requirement: Generic ASGI integration

FastQL SHALL provide a third-party-dependency-free ASGI 3 application that can run directly or be mounted by an ASGI host. It SHALL handle HTTP scopes through the shared integration contract and SHALL not claim unsupported scope types.

#### Scenario: Mounted ASGI execution

- **WHEN** the FastQL ASGI application is mounted at a configured path and receives an HTTP GraphQL request
- **THEN** it reads the ASGI request messages, executes the shared handler, and sends a valid ASGI response

#### Scenario: Unsupported ASGI scope

- **WHEN** the application receives a non-HTTP scope that it does not implement
- **THEN** it declines or closes that scope according to ASGI conventions without attempting GraphQL execution

### Requirement: Starlette integration

FastQL SHALL provide a Starlette-native router or route factory that uses Starlette request and response objects, composes with Starlette mounts and middleware, and exposes the shared FastQL configuration options.

#### Scenario: Starlette routes are registered

- **WHEN** a user adds the FastQL Starlette integration to a Starlette application
- **THEN** the configured GraphQL and enabled companion routes are available through the application's router

### Requirement: FastAPI integration

FastQL SHALL provide an `APIRouter`-compatible FastAPI integration that supports FastAPI router dependencies, tags, and OpenAPI inclusion controls while preserving the shared FastQL execution behavior.

#### Scenario: FastAPI dependency protects GraphQL

- **WHEN** a user configures a FastAPI dependency on the FastQL router
- **THEN** FastAPI resolves that dependency before the GraphQL operation is executed

#### Scenario: Router is included under a prefix

- **WHEN** the FastQL router is included in a FastAPI application with a framework prefix
- **THEN** all enabled integration routes are reachable beneath that prefix

### Requirement: Flask integration

FastQL SHALL provide a Flask `Blueprint` integration that uses Flask request and response objects, supports application or blueprint URL prefixes, and safely bridges the asynchronous FastQL handler from a synchronous Flask request.

#### Scenario: Flask blueprint execution

- **WHEN** a user registers the FastQL blueprint on a Flask application and posts a GraphQL operation
- **THEN** Flask invokes the shared handler and returns a Flask response containing the GraphQL result

### Requirement: Django integration

FastQL SHALL provide an async-capable Django class-based view and URL-pattern helper that use Django request and response objects, cooperate with Django middleware, and make CSRF behavior explicit and configurable.

#### Scenario: Django URL pattern execution

- **WHEN** a user includes the FastQL URL patterns in a Django project
- **THEN** the configured GraphQL and enabled companion endpoints execute through the shared handler

#### Scenario: Django CSRF is secure by default

- **WHEN** the Django adapter is used without an explicit CSRF exemption
- **THEN** the project's normal Django CSRF policy remains in effect

### Requirement: Consistent adapter configuration

Every framework integration SHALL use consistent names and semantics for schema, GraphQL path, context factory, root value, GraphiQL, schema routes, and execution options while returning framework-native registration objects.

#### Scenario: Application changes framework

- **WHEN** an application moves equivalent FastQL configuration from one supported adapter to another
- **THEN** shared options retain their meaning and only the framework-native mounting code changes

### Requirement: Adapter extension contract

FastQL SHALL document the normalized request, response, context, and handler boundary required to add a future framework adapter without modifying the GraphQL executor.

#### Scenario: Third-party adapter delegates execution

- **WHEN** an integration author implements native request and response conversion against the extension contract
- **THEN** the adapter can execute FastQL operations without importing or changing executor internals
