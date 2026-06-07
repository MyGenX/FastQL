## ADDED Requirements

### Requirement: Unified class definition contract
`@Type`, `@Interface`, `@Input`, `@Query`, `@Mutation`, and `@Subscription` SHALL use the same annotation and metadata collection contract. Plain annotations SHALL define fields, and `Field` SHALL define output fields as an attribute, method decorator, or resolver-backed attribute.

#### Scenario: Equivalent fields across definitions
- **WHEN** object, interface, query, mutation, and subscription classes declare an annotated `Field`
- **THEN** name, description, type, deprecation, resolver, arguments, directives, permissions, and extensions are interpreted consistently

#### Scenario: Input field declaration
- **WHEN** an input class uses a plain annotation or input-compatible `Field` metadata
- **THEN** the compiler creates an input field and rejects resolver-only output metadata

### Requirement: Resolver argument metadata
Resolver parameters SHALL derive GraphQL arguments from Python annotations and SHALL accept metadata through `Annotated[T, Argument(...)]` or an equivalent `Arg(...)` default.

#### Scenario: Annotated argument name
- **WHEN** a resolver parameter is annotated with `Annotated[int, Argument(name="userId")]`
- **THEN** the GraphQL argument is named `userId` and retains type `Int!`

### Requirement: Configurable GraphQL naming
Schema construction SHALL convert Python field and argument names from snake_case to camelCase by default, SHALL allow this conversion to be disabled at schema level, and SHALL always honor explicit names.

#### Scenario: Default camel case
- **WHEN** a field named `full_name` has no explicit GraphQL name
- **THEN** its default schema name is `fullName`

#### Scenario: Conversion disabled
- **WHEN** the schema config disables automatic camel casing
- **THEN** the GraphQL name remains `full_name`

## REMOVED Requirements

### Requirement: Operation decorators
**Reason**: Standalone function registration conflicts with the unified class definition and root lifecycle model.
**Migration**: Move each operation resolver to a `@Field` method or resolver-backed attribute on a decorated `@Query`, `@Mutation`, or `@Subscription` class.
