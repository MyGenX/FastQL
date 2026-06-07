## ADDED Requirements

### Requirement: Normalized schema metadata
Field, argument, input-field, and named-type IR SHALL carry explicit Python names, GraphQL metadata, and applied directive values required by schema printing, introspection, and execution.

#### Scenario: Metadata survives compilation
- **WHEN** a decorated field declares a description, deprecation, directive, permission, or extension
- **THEN** the compiled IR preserves the applicable metadata without changing its GraphQL type
