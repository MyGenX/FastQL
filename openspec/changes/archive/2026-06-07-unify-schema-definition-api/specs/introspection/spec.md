## ADDED Requirements

### Requirement: Introspect normalized definitions
Introspection and SDL printing SHALL expose final configured GraphQL names, descriptions, defaults, deprecations, and directive definitions from the compiled schema.

#### Scenario: Camel-cased introspection
- **WHEN** automatic camel casing renames a Python field during schema construction
- **THEN** introspection and SDL expose only the final GraphQL field name
