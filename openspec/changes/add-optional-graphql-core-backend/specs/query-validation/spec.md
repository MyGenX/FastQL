## MODIFIED Requirements

### Requirement: Validate an operation against the schema

The framework SHALL validate a parsed document through the schema's selected operation backend and SHALL return a list of normalized validation errors, empty when the document is valid. The FastQL backend SHALL retain the existing FastQL validation rules. The GraphQL-core backend SHALL use its configured native validation rules and limits against the compiled native schema. Validation SHALL reject documents owned by a different backend and SHALL carry relevant source locations on every normalized error.

#### Scenario: Unknown field

- **WHEN** a query selects a field that does not exist on its parent type
- **THEN** the selected backend returns a normalized error naming the unknown field and execution does not proceed

#### Scenario: Unknown argument

- **WHEN** a field is given an argument that is not defined for that field
- **THEN** the selected backend returns a normalized error naming the unknown argument

#### Scenario: Undefined variable

- **WHEN** a query uses a variable that is not declared in the operation's variable definitions
- **THEN** the selected backend returns a normalized error naming the undefined variable

#### Scenario: Valid operation

- **WHEN** a backend-owned syntactically correct document selects only existing fields with valid arguments and variables
- **THEN** validation returns an empty error list

#### Scenario: Custom GraphQL-core validation rules

- **WHEN** `GraphQLCoreBackend` is configured with an explicit validation rule collection
- **THEN** standalone and execution-time validation use that collection with the configured maximum error count

#### Scenario: Foreign backend document

- **WHEN** standalone validation receives a document not owned by the schema's backend
- **THEN** it returns one actionable backend-document error without running validation rules
