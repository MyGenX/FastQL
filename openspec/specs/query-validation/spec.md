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

### Requirement: No fragment cycles

Validation SHALL reject documents whose fragment spreads form a cycle.

#### Scenario: Cyclic fragments rejected

- **WHEN** fragment A spreads B and B spreads A
- **THEN** validation reports a fragment-cycle error and execution does not run

### Requirement: Known and located directives

Validation SHALL reject directives that are not defined by the schema or that are
used in a location not allowed by their definition.

#### Scenario: Unknown directive rejected

- **WHEN** a query uses `@unknownDirective`
- **THEN** validation reports an unknown-directive error

#### Scenario: Misplaced directive rejected

- **WHEN** a directive valid only on fields is used on a fragment definition
- **THEN** validation reports a directive-location error

### Requirement: Possible fragment spreads

Validation SHALL reject a fragment spread whose type condition cannot apply to
the parent type in context.

#### Scenario: Incompatible spread rejected

- **WHEN** a fragment on type `Dog` is spread within a selection on unrelated type `Cat`
- **THEN** validation reports an impossible-spread error

### Requirement: Lone anonymous operation

Validation SHALL reject a document that combines an anonymous operation with any
other operation.

#### Scenario: Anonymous plus named rejected

- **WHEN** a document contains one anonymous operation and one named operation
- **THEN** validation reports a lone-anonymous-operation error

### Requirement: Uniqueness rules

Validation SHALL reject duplicate operation names, duplicate variable names within
an operation, duplicate argument names on a field, and duplicate input object
field names in a literal.

#### Scenario: Duplicate operation names rejected

- **WHEN** two operations share the same name
- **THEN** validation reports a duplicate-operation-name error

#### Scenario: Duplicate argument names rejected

- **WHEN** a field lists the same argument twice
- **THEN** validation reports a duplicate-argument error

### Requirement: Overlapping fields can be merged

Validation SHALL reject selection sets where fields with the same response key
cannot be merged (conflicting field names, arguments, or response shapes).

#### Scenario: Conflicting aliases rejected

- **WHEN** two selections share a response key but resolve to different fields or arguments
- **THEN** validation reports a fields-conflict error

