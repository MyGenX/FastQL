## ADDED Requirements

### Requirement: Per-member enum value customization

The `@Enum` authoring surface SHALL allow customizing individual enum members'
GraphQL name, description, and deprecation reason, while defaulting to the Python
member name when not overridden.

#### Scenario: Member description applied

- **WHEN** an enum member is annotated with a description
- **THEN** that description appears for the value in the schema and introspection

#### Scenario: Member deprecation applied

- **WHEN** an enum member is marked deprecated with a reason
- **THEN** the SDL renders that value with `@deprecated(reason: ...)`

#### Scenario: Member GraphQL name override

- **WHEN** an enum member is given an explicit GraphQL name
- **THEN** the schema exposes the value under that name instead of the Python member name
