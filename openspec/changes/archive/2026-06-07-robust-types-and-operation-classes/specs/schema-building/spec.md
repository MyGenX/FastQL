## ADDED Requirements

### Requirement: Compose roots from multiple operation containers

`build_schema` SHALL assemble each root operation type by merging the fields contributed by all
registered operations of that kind — whether declared as standalone functions or as methods/attributes
across multiple container classes. When two contributions register the same field name on the same
operation type, the framework SHALL raise a descriptive error identifying the duplicated field.

#### Scenario: Multiple query classes merge

- **WHEN** two separate classes are decorated with `@Query`, one exposing `user` and the other exposing `books`
- **THEN** `build_schema()` produces a query root exposing both `user` and `books`

#### Scenario: Functions and classes compose

- **WHEN** a free `@Query` function and a `@Query` class are both registered with distinct field names
- **THEN** the query root exposes all of their fields

#### Scenario: Duplicate field name across containers

- **WHEN** two registered query operations both define a field named `user`
- **THEN** building the schema raises an error naming the duplicated field
