## ADDED Requirements

### Requirement: Build a schema from registered definitions

The framework SHALL provide `build_schema(query=..., mutation=..., subscription=..., types=[...])`
that compiles the registered decorated definitions into a `Schema` IR. Building SHALL resolve all
forward and circular type references and SHALL include any explicitly listed types that are not
otherwise reachable from the roots.

#### Scenario: Building from a query root

- **WHEN** `build_schema(query=Query)` is called and `Query` references the `User` type
- **THEN** the returned schema exposes the query root and a type map containing `User`

#### Scenario: Circular references resolved

- **WHEN** two `@Type` classes reference each other through forward references
- **THEN** `build_schema` resolves both references and the resulting field types point to the correct types

#### Scenario: Explicitly included type

- **WHEN** a type is passed via the `types=[...]` argument but is not reachable from any root
- **THEN** the schema's type map still includes that type

### Requirement: Validate schema completeness at build time

`build_schema` SHALL validate the assembled schema and raise a descriptive error when a referenced
type is unregistered, when type names collide, when an object type fails to implement a declared
interface's fields, or when a union member is not an object type.

#### Scenario: Unresolved type reference

- **WHEN** a field references a type name that was never registered
- **THEN** `build_schema` raises an error naming the missing type and the field that referenced it

#### Scenario: Duplicate type name

- **WHEN** two distinct definitions register the same GraphQL type name
- **THEN** `build_schema` raises an error reporting the duplicated name

#### Scenario: Interface not satisfied

- **WHEN** an object type declares an interface but omits one of the interface's required fields
- **THEN** `build_schema` raises an error identifying the missing field and the interface
