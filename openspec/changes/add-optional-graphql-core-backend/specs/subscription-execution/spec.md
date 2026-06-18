## MODIFIED Requirements

### Requirement: Subscription execution entrypoint

FastQL SHALL expose an async subscription API that routes source parsing, validation, stream creation, and per-event execution through the schema's selected operation backend and returns either an async iterator of normalized FastQL `ExecutionResult` values or one initial error result. GraphQL-core mode SHALL use native `subscribe` with adapted FastQL resolvers and SHALL retain request-scoped dependency, context, extension, masking, and cleanup state for every iterator step.

#### Scenario: Initial errors returned without a stream

- **WHEN** a subscription document fails the selected backend's parsing or validation, contains a foreign document type, or the root resolver raises before yielding
- **THEN** the entrypoint returns one normalized error `ExecutionResult` rather than an async iterator

#### Scenario: Per-event resolver errors are isolated

- **WHEN** executing the native or FastQL selection set for one yielded event raises
- **THEN** that event's normalized result carries the error and the stream continues with subsequent events

#### Scenario: GraphQL-core subscription context retained

- **WHEN** a GraphQL-core-backed subscription yields events after initial stream creation
- **THEN** each event retains the original user context, dependency cache, FastQL `Info`, permissions, and resolver extensions

#### Scenario: Native GraphQL-core document subscription

- **WHEN** a GraphQL-core-backed schema receives a native subscription `DocumentNode`
- **THEN** it validates and subscribes without converting the document to FastQL AST

### Requirement: Subscription cleanup

FastQL SHALL close the underlying backend subscription iterator when a consumer stops iterating or the connection closes, so resolver and backend cleanup run. GraphQL-core execution state SHALL be reset after each iterator step and final closure.

#### Scenario: Generator closed on cancellation

- **WHEN** the consumer cancels iteration of a subscription stream under either backend
- **THEN** the underlying async iterator's `aclose()` is invoked and backend request state is released
