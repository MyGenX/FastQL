# subscription-execution Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: Async-generator subscription resolution

FastQL SHALL execute `subscription` operations by invoking the root field's
resolver to obtain an async iterator (async generator), then producing one
`ExecutionResult` per yielded source value by executing the selection set against
that value.

#### Scenario: Stream yields a result per event

- **WHEN** a subscription resolver yields three source values
- **THEN** the subscription stream produces three `ExecutionResult` objects, each shaped by the subscription selection set

#### Scenario: Single root field enforced

- **WHEN** a subscription operation selects more than one root field
- **THEN** validation reports an error and no stream is started

### Requirement: Subscription execution entrypoint

FastQL SHALL expose an async API (e.g. `subscribe(schema, document, ...)`) that
returns either an async iterator of results or an initial error result, mirroring
`execute` for queries/mutations.

#### Scenario: Initial errors returned without a stream

- **WHEN** a subscription document fails validation or the root resolver raises before yielding
- **THEN** the entrypoint returns a single error `ExecutionResult` rather than an async iterator

#### Scenario: Per-event resolver errors are isolated

- **WHEN** executing the selection set for one yielded event raises
- **THEN** that event's result carries the error and the stream continues with subsequent events

### Requirement: Subscription cleanup

FastQL SHALL close the underlying async generator when a subscription consumer
stops iterating or the connection closes, so resolver cleanup (`finally`) runs.

#### Scenario: Generator closed on cancellation

- **WHEN** the consumer cancels iteration of a subscription stream
- **THEN** the source async generator's `aclose()` is invoked

