# testing-utilities Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: GraphQL test client

FastQL SHALL provide a `GraphQLTestClient` that executes operations against a
schema (without HTTP) and returns the `ExecutionResult`, accepting a query string,
variables, operation name, and a context.

#### Scenario: Query executed in a test

- **WHEN** a test calls the client with a query and variables
- **THEN** it returns an `ExecutionResult` with `data` and `errors` populated as the executor produced them

#### Scenario: Context supplied per call

- **WHEN** a test passes a context to the client
- **THEN** resolvers receive that context via dependency injection

### Requirement: Subscription testing support

The test client SHALL support subscribing to an operation and collecting the
stream of results for assertions.

#### Scenario: Subscription results collected

- **WHEN** a test subscribes through the client and the resolver yields several events
- **THEN** the client yields the corresponding sequence of `ExecutionResult`s for assertion

