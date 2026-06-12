## ADDED Requirements

### Requirement: Types from Pydantic models

FastQL SHALL provide an optional integration (behind an extra) that derives a
GraphQL object type or input type from a Pydantic model, mapping model fields and
their types, optionality, and defaults to GraphQL fields/arguments.

#### Scenario: Object type generated from model

- **WHEN** a Pydantic model is registered as a FastQL output type
- **THEN** the schema exposes a GraphQL type with fields matching the model's fields and types

#### Scenario: Input type generated from model

- **WHEN** a Pydantic model is registered as a FastQL input type
- **THEN** the schema exposes a GraphQL input object whose fields carry the model's optionality and defaults

### Requirement: Pydantic validation on inputs

When an input is backed by a Pydantic model, FastQL SHALL construct and validate
the model from coerced GraphQL input values, surfacing validation failures as
GraphQL errors.

#### Scenario: Invalid input surfaces error

- **WHEN** a GraphQL input violates a Pydantic validator
- **THEN** execution returns a GraphQL error describing the validation failure rather than crashing

### Requirement: Core remains dependency-free

The Pydantic integration MUST live behind an optional extra and MUST NOT be
imported by the core package.

#### Scenario: Core imports without Pydantic

- **WHEN** Pydantic is not installed
- **THEN** `import fastql` and core operations succeed unchanged
