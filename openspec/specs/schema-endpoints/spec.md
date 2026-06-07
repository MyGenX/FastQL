# schema-endpoints Specification

## Purpose
HTTP endpoints exposing the schema as SDL (/schema.graphql) and as an introspection result (/schema.json).
## Requirements
### Requirement: Print a schema as SDL

The framework SHALL provide `print_schema(schema)` that renders a built `Schema` into GraphQL Schema
Definition Language (SDL) text. The output SHALL include object, interface, union, enum, input, and scalar
type definitions with their fields, arguments, and default values, and SHALL include deprecation
annotations for deprecated fields, arguments, and enum values.

#### Scenario: Root type in SDL

- **WHEN** `print_schema(schema)` is called for a schema with a query root
- **THEN** the returned text contains a `type Query` block listing the query fields and their types

#### Scenario: Deprecation rendered

- **WHEN** a field is marked deprecated in the schema
- **THEN** the SDL renders that field with a `@deprecated(reason: ...)` annotation

### Requirement: SDL endpoint

The server SHALL serve the schema as SDL text at `GET /schema.graphql` with content type `text/plain`,
using `print_schema`.

#### Scenario: Fetch SDL

- **WHEN** a client requests `GET /schema.graphql`
- **THEN** the response is `200` `text/plain` whose body is the schema's SDL and contains `type Query`

### Requirement: Introspection JSON endpoint

The server SHALL serve the schema's introspection result as JSON at `GET /schema.json` by executing the
standard introspection query through `execute` and returning its `data`.

#### Scenario: Fetch introspection

- **WHEN** a client requests `GET /schema.json`
- **THEN** the response is `200` `application/json` and the body contains a `__schema` object describing the types

### Requirement: Reusable schema endpoint service

Production framework adapters SHALL reuse shared FastQL behavior for the GraphQL execution endpoint, GraphiQL document, SDL document, and introspection JSON document instead of depending on the built-in development server dispatcher.

#### Scenario: SDL is equivalent across adapters

- **WHEN** the same schema is exposed through two supported framework adapters with SDL enabled
- **THEN** both SDL endpoints return the output of `print_schema(schema)` with equivalent content types and bodies

#### Scenario: Introspection JSON is equivalent across adapters

- **WHEN** the same schema is exposed through two supported framework adapters with introspection JSON enabled
- **THEN** both endpoints return equivalent introspection results produced by FastQL execution

### Requirement: Independently configurable companion endpoints

Each framework adapter SHALL allow GraphiQL, SDL, and introspection JSON endpoints to be enabled, disabled, or assigned paths independently of the GraphQL execution path. Route registration SHALL respect framework prefixes and mounts.

#### Scenario: Framework prefix composes with endpoint paths

- **WHEN** an adapter with `/graphql` and `/schema.graphql` routes is mounted under `/api`
- **THEN** the framework exposes those routes under `/api/graphql` and `/api/schema.graphql`

#### Scenario: Production schema documents disabled

- **WHEN** an application disables GraphiQL, SDL, and introspection JSON routes
- **THEN** only the GraphQL execution route is registered by the adapter

