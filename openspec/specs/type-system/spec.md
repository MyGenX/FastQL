# type-system Specification

## Purpose
The in-memory GraphQL type-system IR: type definitions, NonNull/List wrappers, built-in scalars, and the Schema container.
## Requirements
### Requirement: Type-system intermediate representation

The framework SHALL provide an in-memory type-system IR that represents GraphQL object, interface,
union, enum, input-object, and scalar types, together with `Field`, `Argument`, and `InputField`
definitions and directive definitions. Output and input positions SHALL be expressible through the
`NonNull` and `List` wrapping types.

#### Scenario: Object type with fields

- **WHEN** an object type is defined with named fields, each carrying a type and optional arguments
- **THEN** the IR exposes the type's name, its fields by name, and each field's type and arguments

#### Scenario: Wrapping types

- **WHEN** a field is declared as a non-null list of non-null strings
- **THEN** the IR represents it as `NonNull(List(NonNull(String)))` and preserves that nesting order

### Requirement: Normalized schema metadata

Field, argument, input-field, and named-type IR SHALL carry explicit Python names, GraphQL metadata,
and applied directive values required by schema printing, introspection, and execution.

#### Scenario: Metadata survives compilation

- **WHEN** a decorated field declares a description, deprecation, directive, permission, or extension
- **THEN** the compiled IR preserves the applicable metadata without changing its GraphQL type

### Requirement: Built-in scalars

The framework SHALL provide the five built-in scalars `Int`, `Float`, `String`, `Boolean`, and `ID`,
each able to serialize internal values to output, coerce input values, and coerce AST literal values.
Coercion failures SHALL raise a typed error rather than returning an invalid value.

#### Scenario: Int serialization

- **WHEN** an `Int` field resolves to the Python value `42`
- **THEN** the scalar serializes it to the integer `42` in the result

#### Scenario: Invalid Int input

- **WHEN** an `Int` argument receives the input value `"abc"`
- **THEN** coercion raises an error describing the invalid `Int` value

#### Scenario: ID accepts string and integer

- **WHEN** an `ID` value is provided as either a string or an integer
- **THEN** coercion succeeds and yields a string representation

### Requirement: Schema container

The framework SHALL provide a `Schema` object that holds the root query type and optional root
mutation and subscription types, exposes a map of all named types reachable from the roots, and
exposes the available directive definitions.

#### Scenario: Reachable type map

- **WHEN** a `Schema` is constructed with a query type that references other object and scalar types
- **THEN** the schema's type map contains every type reachable from the query root, keyed by name
