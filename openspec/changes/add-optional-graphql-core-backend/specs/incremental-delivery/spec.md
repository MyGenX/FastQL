## MODIFIED Requirements

### Requirement: @defer directive

The FastQL operation backend SHALL support the `@defer` directive on fragments so incremental execution omits the deferred selection from the initial response and delivers it in a later payload. The GraphQL-core 3.2 backend SHALL support the directive definition for ordinary non-streaming validation/execution but SHALL reject `execute_incremental` with one actionable terminal error payload and SHALL NOT fall back to FastQL or prerelease APIs.

#### Scenario: Deferred fragment delivered later

- **WHEN** a FastQL-backed query marks a fragment with `@defer` and uses incremental execution
- **THEN** the initial result contains `hasNext: true` without the deferred data and a later payload carries the deferred selection at its path

#### Scenario: @defer(if: false) inlines

- **WHEN** `@defer(if: false)` is applied under the FastQL backend
- **THEN** the selection is resolved inline in the initial result with no incremental payload

#### Scenario: GraphQL-core incremental defer rejected

- **WHEN** `execute_incremental` is called for a GraphQL-core-backed schema using `@defer`
- **THEN** it yields one payload with `data: null`, an actionable error, and `hasNext: false`

### Requirement: @stream directive

The FastQL operation backend SHALL support the `@stream` directive on list fields so initial items are returned immediately and remaining items arrive in later payloads. The GraphQL-core 3.2 backend SHALL reject incremental stream execution explicitly and SHALL NOT switch engines.

#### Scenario: List streamed in chunks

- **WHEN** a FastQL-backed list field is annotated `@stream(initialCount: 1)` and uses incremental execution
- **THEN** the initial result contains one item and subsequent items arrive as incremental payloads appended at the list path

#### Scenario: GraphQL-core incremental stream rejected

- **WHEN** `execute_incremental` is called for a GraphQL-core-backed schema using `@stream`
- **THEN** it yields one payload with an actionable unsupported-backend error and `hasNext: false`

### Requirement: Incremental delivery requires a streaming transport

Incremental FastQL-backend payloads SHALL be delivered only over a streaming-capable transport. A non-streaming transport SHALL call ordinary execution and return one fully resolved result. When a streaming transport detects incremental directives for a GraphQL-core-backed schema, it SHALL surface the backend's one terminal unsupported result rather than silently executing with FastQL.

#### Scenario: Non-streaming transport collapses to one result

- **WHEN** a deferred or streamed query is executed through ordinary non-streaming execution
- **THEN** the client receives one complete result according to the selected backend's normal execution behavior

#### Scenario: Streaming GraphQL-core request reports unsupported backend

- **WHEN** a streaming transport submits an incremental query to a GraphQL-core-backed schema
- **THEN** it emits the normalized terminal unsupported payload and closes the stream
