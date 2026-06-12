# field-visibility Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: Private fields excluded from the schema

FastQL SHALL allow a field to be marked private so it is usable on the Python
object but is excluded from the GraphQL schema, SDL, and introspection.

#### Scenario: Private field absent from schema

- **WHEN** a `@Type` declares a field marked private
- **THEN** that field does not appear in the built schema, SDL, or introspection results

#### Scenario: Private field remains usable in Python

- **WHEN** a resolver accesses the private attribute on the object
- **THEN** the attribute is available at runtime despite being absent from the schema

### Requirement: External fields for federation

FastQL SHALL allow a field to be marked external, meaning it is declared in the
SDL (for federation `@external` semantics) but is not resolved locally by this
subgraph.

#### Scenario: External field declared but not resolved

- **WHEN** a field is marked external on a federated type
- **THEN** the field appears in the federated SDL with `@external` and the local executor does not require a resolver for it

