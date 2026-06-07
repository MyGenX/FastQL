# introspection Specification

## Purpose
The GraphQL introspection meta-fields __schema, __type, and __typename.
## Requirements
### Requirement: Introspection meta-fields

The schema SHALL support the GraphQL introspection meta-fields `__schema` and `__type(name:)` on the
query root and `__typename` on every object, interface, and union type. Introspection SHALL report
the schema's types, each type's kind, fields, arguments, enum values, interfaces, and possible types,
and the field/argument/enum-value deprecation status — sufficient for standard GraphQL tooling.

#### Scenario: Schema type listing

- **WHEN** the query `{ __schema { types { name kind } } }` is executed
- **THEN** the result lists every type in the schema with its name and kind

#### Scenario: Type lookup by name

- **WHEN** the query `{ __type(name: "User") { name fields { name } } }` is executed
- **THEN** the result describes the `User` type and its fields

#### Scenario: Typename on a selection

- **WHEN** a selection set on an object type includes `__typename`
- **THEN** the result includes the concrete type's name for that object

### Requirement: Introspect normalized definitions

Introspection and SDL printing SHALL expose final configured GraphQL names, descriptions, defaults,
deprecations, and directive definitions from the compiled schema.

#### Scenario: Camel-cased introspection

- **WHEN** automatic camel casing renames a Python field during schema construction
- **THEN** introspection and SDL expose only the final GraphQL field name
