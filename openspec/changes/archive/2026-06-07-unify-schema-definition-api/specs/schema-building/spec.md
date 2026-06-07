## ADDED Requirements

### Requirement: Construct schema from decorated roots
The framework SHALL provide `Schema(query=..., mutation=..., subscription=..., types=[...], config=...)` as the canonical schema API and SHALL compile fresh IR from decorated definitions.

#### Scenario: Explicit query root
- **WHEN** `Schema(query=Query)` receives a decorated query class
- **THEN** it exposes the class fields as the query root using the schema naming configuration

### Requirement: Discover and merge roots
Zero-argument `build_schema()` SHALL discover all decorated root classes, merge distinct fields by operation kind, and reject duplicate final GraphQL names.

#### Scenario: Multiple query classes
- **WHEN** two query classes expose distinct fields
- **THEN** auto-discovery builds one query root containing both fields
