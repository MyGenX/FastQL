# schema-definition Specification

## Purpose
The decorator authoring surface and Python type-hint to GraphQL type inference.
## Requirements
### Requirement: Unified class definition contract

`@Type`, `@Interface`, `@Input`, `@Query`, `@Mutation`, and `@Subscription` SHALL use the same
annotation and metadata collection contract. Plain annotations SHALL define fields, and `Field` SHALL
define output fields as an attribute, method decorator, or resolver-backed attribute.

#### Scenario: Equivalent fields across definitions

- **WHEN** object, interface, query, mutation, and subscription classes declare an annotated `Field`
- **THEN** name, description, type, deprecation, resolver, arguments, directives, permissions, and extensions are interpreted consistently

#### Scenario: Input field declaration

- **WHEN** an input class uses a plain annotation or input-compatible `Field` metadata
- **THEN** the compiler creates an input field and rejects resolver-only output metadata

### Requirement: Resolver argument metadata

Resolver parameters SHALL derive GraphQL arguments from Python annotations and SHALL accept metadata
through `Annotated[T, Argument(...)]` or an equivalent `Arg(...)` default.

#### Scenario: Annotated argument name

- **WHEN** a resolver parameter is annotated with `Annotated[int, Argument(name="userId")]`
- **THEN** the GraphQL argument is named `userId` and retains type `Int!`

### Requirement: Configurable GraphQL naming

Schema construction SHALL convert Python field and argument names from snake_case to camelCase by
default, SHALL allow this conversion to be disabled at schema level, and SHALL always honor explicit
names.

#### Scenario: Default camel case

- **WHEN** a field named `full_name` has no explicit GraphQL name
- **THEN** its default schema name is `fullName`

#### Scenario: Conversion disabled

- **WHEN** the schema config disables automatic camel casing
- **THEN** the GraphQL name remains `full_name`

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

### Requirement: Auto-generated object constructors

When a class decorated with `@Type` does not define its own `__init__`, the framework SHALL
synthesize a constructor accepting each data field as both a positional and a keyword argument, in
declaration order, applying declared defaults. The framework SHALL also synthesize `__repr__` and
`__eq__` when the class does not define them. Computed fields (resolver-backed) SHALL NOT be
constructor parameters. A user-defined `__init__`, `__repr__`, or `__eq__` SHALL be preserved.

#### Scenario: Positional and keyword construction

- **WHEN** a `@Type` class declares only `id: int` and `name: str` and defines no `__init__`
- **THEN** both `User(1, "Ada")` and `User(id=1, name="Ada")` create an instance with those attribute values

#### Scenario: Defaults are honored

- **WHEN** a data field declares a default (e.g. `active: bool = True`)
- **THEN** the synthesized constructor uses that default when the argument is omitted

#### Scenario: Generated repr and eq

- **WHEN** two instances of an autogenerated `@Type` hold equal field values
- **THEN** they compare equal and their `repr` lists the field values

#### Scenario: User-defined constructor is preserved

- **WHEN** a `@Type` class defines its own `__init__`
- **THEN** the framework does not overwrite it

### Requirement: Resolver-backed fields via Field(resolver=...)

The framework SHALL support declaring a computed field as an annotated attribute assigned
`Field(resolver=fn)`. The GraphQL field name SHALL default to the attribute name, the field type
SHALL come from the annotation (or an explicit `Field(type=...)`), and the field SHALL be resolved by
calling `fn`. Such attributes SHALL NOT be constructor parameters.

#### Scenario: Attribute resolver field

- **WHEN** a type declares `books: list[Book] = Field(resolver=get_books)`
- **THEN** the framework registers a `books` field of type `[Book!]!` whose resolver is `get_books`

#### Scenario: Resolver field excluded from the constructor

- **WHEN** a `@Type` has a `Field(resolver=...)` attribute and an autogenerated constructor
- **THEN** that attribute is not a constructor parameter

### Requirement: Operation container classes

The framework SHALL allow `@Query`, `@Mutation`, and `@Subscription` to decorate a class. Each
`@Field`-decorated method and each `Field(resolver=...)` attribute on the class SHALL register a root
field on the corresponding operation type. `@Field` methods SHALL be bound to an instance created once
per GraphQL operation so that `self` refers to request-local root state and is excluded from the
field's GraphQL arguments. Undecorated methods SHALL be ignored.

#### Scenario: Query class with multiple fields

- **WHEN** a class decorated with `@Query` defines two `@Field` methods `user` and `ping`
- **THEN** the schema's query root exposes both `user` and `ping` fields, and `self` is not a GraphQL argument

#### Scenario: Mutation and subscription classes

- **WHEN** a class is decorated with `@Mutation` (or `@Subscription`)
- **THEN** its `@Field` methods register as fields on the mutation (or subscription) root type

#### Scenario: Undecorated methods are ignored

- **WHEN** an operation container class defines a plain helper method without `@Field`
- **THEN** that method does not become a GraphQL field

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

