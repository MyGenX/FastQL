## ADDED Requirements

### Requirement: Author-defined schema directives

FastQL SHALL provide a `@Directive` authoring API for defining custom schema
directives with a name, declared `locations`, optional arguments (inferred from
type hints), repeatability, and a description.

#### Scenario: Directive definition registered

- **WHEN** a custom directive is defined with locations and arguments
- **THEN** a `DirectiveDefinition` is registered on the schema and appears in introspection

#### Scenario: Location enforced

- **WHEN** a custom directive declared only for `FIELD_DEFINITION` is applied to an object type
- **THEN** schema building reports an invalid-location error

### Requirement: Applying custom directives to definitions

Custom directives SHALL be applicable to schema definitions (types, fields,
arguments, enum values, etc.) with argument values, and SHALL be rendered in the
SDL output.

#### Scenario: Applied directive rendered in SDL

- **WHEN** a field is annotated with an applied custom directive carrying arguments
- **THEN** the SDL renders the directive with its argument values on that field

#### Scenario: Directive arguments coerced

- **WHEN** an applied directive supplies argument values
- **THEN** those values are validated and coerced against the directive's declared argument types
