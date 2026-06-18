## MODIFIED Requirements

### Requirement: Construct schema from decorated roots

The framework SHALL provide `Schema(query=..., mutation=..., subscription=..., types=[...], config=...)` as the canonical schema API, SHALL compile fresh IR from decorated definitions, and SHALL resolve exactly one schema-wide operation backend from `SchemaConfig.operation_backend`. The backend SHALL default to `"fastql"`; selecting `"graphql-core"` without its optional dependency SHALL fail with an actionable installation message.

#### Scenario: Explicit query root

- **WHEN** `Schema(query=Query)` receives a decorated query class
- **THEN** it exposes the class fields as the query root using the schema naming configuration and the default FastQL operation backend

#### Scenario: GraphQL-core backend selected

- **WHEN** `Schema(query=Query, config=SchemaConfig(operation_backend="graphql-core"))` is built with the optional extra installed
- **THEN** the schema retains the same FastQL IR and selects a lazily compiled GraphQL-core operation backend

#### Scenario: GraphQL-core extra missing

- **WHEN** a schema selects `"graphql-core"` without GraphQL-core installed
- **THEN** construction raises an import error instructing the user to install `fastql[graphql-core]`
