## ADDED Requirements

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
