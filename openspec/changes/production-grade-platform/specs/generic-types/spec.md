## ADDED Requirements

### Requirement: Generic type definitions

FastQL SHALL allow `@Type`/`@Input`/`@Interface` classes to declare `TypeVar`
parameters (via `typing.Generic[T]`) so a single Python class defines a family of
GraphQL types parametrized by other types.

#### Scenario: Generic class accepted

- **WHEN** a class `Connection(Generic[T])` is decorated with `@Type`
- **THEN** schema building accepts it without requiring a concrete type until it is used with a parameter

#### Scenario: Type variable used in a field

- **WHEN** a generic class has a field annotated `list[T]`
- **THEN** the field type is resolved from the concrete parameter at the usage site

### Requirement: Concrete type synthesis and naming

When a generic type is used with a concrete parameter, FastQL SHALL synthesize a
distinct concrete GraphQL type whose name is derived from the parameter (e.g.
`UserConnection` for `Connection[User]`), reusing one synthetic type per unique
parametrization.

#### Scenario: Stable synthetic name

- **WHEN** `Connection[User]` is referenced in two places
- **THEN** a single GraphQL type named `UserConnection` exists in the schema and both references point to it

#### Scenario: Distinct parametrizations are distinct types

- **WHEN** both `Connection[User]` and `Connection[Post]` are used
- **THEN** the schema contains separate `UserConnection` and `PostConnection` types

#### Scenario: Custom naming override

- **WHEN** a name override is supplied for a parametrization
- **THEN** the synthesized type uses that name instead of the derived default
