## ADDED Requirements

### Requirement: Federation directives

FastQL SHALL support Apollo Federation v2 directives on type and field
definitions — `@key`, `@external`, `@shareable`, `@requires`, `@provides`,
`@inaccessible`, `@override`, `@tag` — and render them in the federated SDL with
the `@link` import to the federation spec.

#### Scenario: Entity declared with @key

- **WHEN** a type is marked as an entity with key field(s)
- **THEN** the federated SDL renders the type with `@key(fields: "...")` and includes the federation `@link` header

#### Scenario: Field directives rendered

- **WHEN** a field is marked `@external`/`@shareable`/`@requires`/`@provides`
- **THEN** those directives appear on the field in the federated SDL

### Requirement: _service field

A federated schema SHALL expose the `_service { sdl }` query returning the
federated SDL of the subgraph.

#### Scenario: _service returns SDL

- **WHEN** a gateway queries `{ _service { sdl } }`
- **THEN** the response contains the subgraph's federated SDL string

### Requirement: Entity resolution via _entities

A federated schema SHALL expose `_entities(representations: [_Any!]!): [_Entity]!`
that resolves each representation to its concrete entity using a registered
reference resolver for that type, in input order.

#### Scenario: Representations resolved in order

- **WHEN** a gateway sends representations for two entities of different types
- **THEN** `_entities` returns the resolved objects in the same order, each with the correct `__typename`

#### Scenario: Reference resolver receives key fields

- **WHEN** a representation contains an entity's key fields
- **THEN** the type's reference resolver is invoked with those fields and returns the entity (or null if not found)
