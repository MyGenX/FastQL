## ADDED Requirements

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
