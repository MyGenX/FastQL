## MODIFIED Requirements

### Requirement: Print a schema as SDL

The framework SHALL provide `print_schema(schema)` that renders the schema's publishable GraphQL Schema Definition Language contract. For a normal schema, the output SHALL include its object, interface, union, enum, input, and scalar definitions with fields, arguments, defaults, directives, and deprecations. For `fastql.federation.Schema`, the output SHALL be the gateway-facing federated SDL for the selected Federation version.

#### Scenario: Root type in standard SDL

- **WHEN** `print_schema(schema)` is called for a non-federated schema with a query root
- **THEN** the returned text contains a `type Query` block listing the query fields and their types

#### Scenario: Federated schema uses subgraph SDL

- **WHEN** `print_schema(schema)` is called for a federated schema
- **THEN** the output includes the selected-version federation `@link` and excludes generated federation execution fields and support types

#### Scenario: Deprecation rendered

- **WHEN** a field is marked deprecated in the schema
- **THEN** the SDL renders that field with a `@deprecated(reason: ...)` annotation

### Requirement: SDL endpoint

The server SHALL serve the schema's publishable SDL at `GET /schema.graphql` with content type `text/plain`, using `print_schema` without transport-specific federation branching.

#### Scenario: Fetch standard SDL

- **WHEN** a client requests `GET /schema.graphql` for a non-federated schema
- **THEN** the response is `200` `text/plain` whose body is the schema's standard SDL and contains `type Query`

#### Scenario: Fetch federated SDL

- **WHEN** a client requests `GET /schema.graphql` for a federated schema
- **THEN** the response is `200` `text/plain` and its body is identical to that schema's `_service.sdl` value

### Requirement: Reusable schema endpoint service

Production framework adapters SHALL reuse shared FastQL behavior for the GraphQL execution endpoint, GraphiQL document, SDL document, and introspection JSON document instead of depending on the built-in development server dispatcher. Schema-aware SDL rendering SHALL remain identical across adapters.

#### Scenario: SDL is equivalent across adapters

- **WHEN** the same standard or federated schema is exposed through two supported framework adapters with SDL enabled
- **THEN** both SDL endpoints return the output of `print_schema(schema)` with equivalent content types and bodies

#### Scenario: Introspection JSON is equivalent across adapters

- **WHEN** the same schema is exposed through two supported framework adapters with introspection JSON enabled
- **THEN** both endpoints return equivalent introspection results produced by FastQL execution
