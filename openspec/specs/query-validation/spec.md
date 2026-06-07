# query-validation Specification

## Purpose
Validating a parsed operation against the schema before execution.
## Requirements
### Requirement: Validate an operation against the schema

The framework SHALL validate a parsed document against a built schema before execution and SHALL
return a list of validation errors (empty when the document is valid). Validation SHALL at minimum
verify that selected fields exist on their parent type, that provided arguments are defined and
correctly typed, that fragments reference existing types and are spread on compatible types, and that
variables are defined and used consistently. Each validation error SHALL carry a message and the
relevant source location.

#### Scenario: Unknown field

- **WHEN** a query selects a field that does not exist on its parent type
- **THEN** validation returns an error naming the unknown field and its location, and execution does not proceed

#### Scenario: Unknown argument

- **WHEN** a field is given an argument that is not defined for that field
- **THEN** validation returns an error naming the unknown argument

#### Scenario: Undefined variable

- **WHEN** a query uses a variable that is not declared in the operation's variable definitions
- **THEN** validation returns an error naming the undefined variable

#### Scenario: Valid operation

- **WHEN** a syntactically correct query selects only existing fields with valid arguments and variables
- **THEN** validation returns an empty error list

