## MODIFIED Requirements

### Requirement: Federation directives

FastQL SHALL support the Apollo Federation v2 directives available in each supported selected version and SHALL default `fastql.federation.Schema` to the release-pinned latest supported version, Federation v2.14. The v2.14 surface SHALL include `@key`, `@external`, `@requires`, `@provides`, `@extends`, `@shareable`, `@override`, `@tag`, `@inaccessible`, `@composeDirective`, `@interfaceObject`, `@authenticated`, `@requiresScopes`, `@policy`, `@context`, `@fromContext`, `@cost`, `@listSize`, and `@cacheTag`. Federated SDL SHALL render the selected version in its `@link` declaration and import the used federation metadata.

#### Scenario: Latest version used by default

- **WHEN** a federated schema is constructed without an explicit Federation version
- **THEN** the schema uses Federation v2.14 and its federated SDL links to the v2.14 specification

#### Scenario: Explicit supported version selected

- **WHEN** a federated schema selects an older supported Federation v2 version
- **THEN** only directives and argument forms available in that version are accepted and rendered

#### Scenario: Latest directive metadata rendered

- **WHEN** definitions use directives introduced after v2.7 that are available in the selected version
- **THEN** their applications and required linked feature metadata appear in the federated SDL

#### Scenario: Invalid federation directive rejected

- **WHEN** a federation directive has an invalid location, argument, repeated use, or version for the selected schema
- **THEN** schema construction fails with an error identifying the invalid application

### Requirement: _service field

A federated schema SHALL expose the `_service { sdl }` query returning the gateway-facing federated SDL of the subgraph for the selected Federation version. The returned SDL SHALL include federation directive applications and links and SHALL omit generated federation execution fields and support types.

#### Scenario: _service returns publishable subgraph SDL

- **WHEN** a gateway queries `{ _service { sdl } }`
- **THEN** the response contains the selected-version `@link` and user schema definitions without `_service`, `_entities`, `_Any`, `_Entity`, or `_Service` definitions

### Requirement: Entity resolution via _entities

A federated schema SHALL expose `_entities(representations: [_Any!]!): [_Entity]!` when it defines at least one entity with a resolvable `@key`. The schema SHALL resolve valid representations with schema-owned reference resolvers in input order, and SHALL exclude types whose keys are all marked `resolvable: false` from `_Entity`.

#### Scenario: Representations resolved in order

- **WHEN** a gateway sends valid representations for two entities of different types
- **THEN** `_entities` returns the resolved objects in the same order, each with the correct `__typename`

#### Scenario: Reference resolver receives representation data

- **WHEN** a representation satisfies one of an entity's declared resolvable keys
- **THEN** the type's reference resolver can receive the full representation, matching key fields, and resolve info and can return the entity or null when not found

#### Scenario: Non-resolvable entity excluded

- **WHEN** an entity type has only `@key` directives with `resolvable: false`
- **THEN** it remains in federated SDL but is not a member of `_Entity` and does not require a reference resolver

## ADDED Requirements

### Requirement: Federation field-set validation

FastQL SHALL parse and validate field sets used by `@key`, `@requires`, and `@provides` against the applicable schema type during federated schema construction.

#### Scenario: Compound and nested field sets accepted

- **WHEN** a field set contains valid compound or nested selections present on the applicable type
- **THEN** schema construction succeeds and preserves the field set in federated SDL

#### Scenario: Invalid field set rejected

- **WHEN** a field set is malformed or references a field or nested selection that is not valid for the applicable type
- **THEN** schema construction fails with an error identifying the directive and invalid field set

### Requirement: Schema-local reference resolvers

Each federated schema SHALL snapshot its entity reference resolvers during construction and SHALL not consult mutable process-global registrations during execution.

#### Scenario: Schemas with matching entity names remain isolated

- **WHEN** two schemas define different Python entity types with the same GraphQL name and register different resolvers
- **THEN** each schema's `_entities` field invokes only the resolver captured for that schema

#### Scenario: Resolvable entity lacks resolver

- **WHEN** a schema defines an entity with a resolvable key but no applicable reference resolver
- **THEN** schema construction fails with an error naming the entity

### Requirement: Entity representation validation

FastQL SHALL validate every `_entities` representation before invoking a reference resolver. A representation MUST be an object, contain a string `__typename`, target a resolvable entity, and contain all fields of at least one declared resolvable key.

#### Scenario: Representation satisfies alternate key

- **WHEN** an entity has multiple resolvable keys and a representation fully satisfies any one key
- **THEN** FastQL invokes the entity's reference resolver

#### Scenario: Invalid representation reports indexed error

- **WHEN** a representation has a missing or invalid `__typename`, targets an unknown entity, or does not satisfy a resolvable key
- **THEN** `_entities` returns a GraphQL error whose path identifies that representation's list index and does not invoke user resolver code for it

#### Scenario: Valid entity not found

- **WHEN** a valid representation is passed to a reference resolver and the resolver returns null
- **THEN** the corresponding `_entities` result entry is null without treating the representation as malformed
