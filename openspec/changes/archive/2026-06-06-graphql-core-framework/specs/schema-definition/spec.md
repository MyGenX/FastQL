## ADDED Requirements

### Requirement: Object and input type decorators

The framework SHALL provide `@Type`, `@Input`, and `@Interface` decorators that register a Python
class as a GraphQL object, input-object, or interface type. The type's name SHALL default to the
class name and each annotated class attribute SHALL become a GraphQL field or input field.

#### Scenario: Defining an object type

- **WHEN** a class annotated with `@Type` declares attributes `id: int` and `name: str`
- **THEN** the framework registers an object type with fields `id` of type `Int!` and `name` of type `String!`

#### Scenario: Interface implementation

- **WHEN** a `@Type` class is declared as implementing an `@Interface` class
- **THEN** the registered object type lists that interface and inherits its required fields

### Requirement: Type inference from Python type hints

The framework SHALL infer GraphQL field and argument types from Python type hints: `int` to `Int`,
`float` to `Float`, `str` to `String`, `bool` to `Boolean`, a dedicated `ID` marker to `ID`,
`X | None` / `Optional[X]` to a nullable type, `list[X]` to a `List` wrapper, `Enum` subclasses to
GraphQL enums, and registered `@Type`/`@Input` classes (including string forward references) to their
corresponding GraphQL types. A bare (non-optional) hint SHALL map to a `NonNull` type.

#### Scenario: Optional and list inference

- **WHEN** a field is annotated `friends: list["User"] | None`
- **THEN** the framework infers the GraphQL type `[User!]` (nullable list of non-null `User`)

#### Scenario: Forward reference

- **WHEN** a field on `User` is annotated with the string forward reference `"User"`
- **THEN** the reference is recorded as a thunk and resolves to the `User` type at schema-build time

### Requirement: Field descriptor overrides

The framework SHALL provide a `Field(...)` descriptor usable as an attribute default
(`name: str = Field(description="...")`) and an `@Field` decorator for computed/method-backed fields.
`Field(...)` SHALL allow overriding the GraphQL field name, description, deprecation reason, and the
resolved type, without removing the type inferred from the hint unless an explicit type is supplied.

#### Scenario: Description and deprecation override

- **WHEN** an attribute is declared `legacy: str = Field(deprecated="use modern")`
- **THEN** the registered field is marked deprecated with reason `"use modern"` while keeping type `String!`

#### Scenario: Computed field

- **WHEN** a method on a `@Type` class is decorated with `@Field` and annotated to return `str`
- **THEN** the framework registers a `String!` field whose value comes from invoking that method

### Requirement: Enum, union, and scalar decorators

The framework SHALL provide `@Enum` to register a Python `Enum` as a GraphQL enum, `@Union` to declare
a union over registered object types, and `@Scalar` to register a custom scalar with serialize and
parse behavior.

#### Scenario: Enum registration

- **WHEN** a Python `Enum` is decorated with `@Enum`
- **THEN** the framework registers a GraphQL enum whose values are the enum members' names

#### Scenario: Union registration

- **WHEN** `@Union` declares a union over two registered `@Type` classes
- **THEN** the framework registers a union type whose members are those two object types

### Requirement: Operation decorators

The framework SHALL provide `@Query`, `@Mutation`, and `@Subscription` decorators that register a
function (or method) as a root field on the query, mutation, or subscription type. The field name
SHALL default to the function name, the return hint SHALL determine the field type, and parameters
SHALL determine the field's GraphQL arguments (excluding injected parameters such as context and info).

#### Scenario: Registering a query

- **WHEN** a function `def user(id: int) -> "User"` is decorated with `@Query`
- **THEN** the framework registers a root query field `user` of type `User` with one argument `id` of type `Int!`

#### Scenario: Mutation registration

- **WHEN** a function is decorated with `@Mutation`
- **THEN** the framework registers it as a field on the root mutation type
