# incremental-delivery Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: @defer directive

FastQL SHALL support the `@defer` directive on fragments so the initial response
omits the deferred selection and a subsequent incremental payload delivers it.

#### Scenario: Deferred fragment delivered later

- **WHEN** a query marks a fragment with `@defer`
- **THEN** the initial result contains `hasNext: true` without the deferred data, and a later incremental payload carries the deferred selection at its path

#### Scenario: @defer(if: false) inlines

- **WHEN** `@defer(if: false)` is applied
- **THEN** the selection is resolved inline in the initial result with no incremental payload

### Requirement: @stream directive

FastQL SHALL support the `@stream` directive on list fields so initial items are
returned immediately and remaining items arrive in incremental payloads.

#### Scenario: List streamed in chunks

- **WHEN** a list field is annotated `@stream(initialCount: 1)`
- **THEN** the initial result contains one item and subsequent items arrive as incremental payloads appended at the list path

### Requirement: Incremental delivery requires a streaming transport

Incremental payloads SHALL be delivered only over a streaming-capable transport
(multipart/SSE); over a non-streaming transport the response SHALL be returned as
a single fully-resolved result.

#### Scenario: Non-streaming transport collapses to one result

- **WHEN** a deferred/streamed query is executed over a non-streaming transport
- **THEN** the client receives a single complete result with all selections resolved

