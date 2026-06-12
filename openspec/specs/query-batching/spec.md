# query-batching Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: Batched operations in one request

The HTTP integration layer SHALL accept a JSON array of operation payloads in a
single POST and execute each, returning a JSON array of results positionally
aligned to the requests.

#### Scenario: Array request returns array response

- **WHEN** a POST body is a JSON array of two valid operation payloads
- **THEN** the response is a JSON array of two results in the same order

#### Scenario: Per-operation errors isolated

- **WHEN** one operation in a batch fails and another succeeds
- **THEN** each array entry independently carries its own `data`/`errors`

### Requirement: Batching configurable and bounded

Query batching SHALL be configurable (enabled/disabled) and SHALL enforce a
maximum batch size, rejecting oversized batches with a client error.

#### Scenario: Batching disabled rejects arrays

- **WHEN** batching is disabled and an array body is received
- **THEN** the request is rejected with a 400-level error

#### Scenario: Oversized batch rejected

- **WHEN** a batch exceeds the configured maximum size
- **THEN** the request is rejected with a client error before execution

