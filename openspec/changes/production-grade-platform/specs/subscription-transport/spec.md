## ADDED Requirements

### Requirement: graphql-transport-ws WebSocket protocol

The integrations layer SHALL provide a WebSocket handler implementing the
`graphql-transport-ws` sub-protocol (ConnectionInit/Ack, Subscribe, Next, Error,
Complete, Ping/Pong) that drives subscription streams via the core subscription
entrypoint. This handler MUST NOT be imported by the dependency-free core.

#### Scenario: Subscribe produces Next messages

- **WHEN** a client sends `connection_init` then `subscribe` with a subscription document
- **THEN** the server replies `connection_ack`, emits a `next` message per event, and a `complete` message when the stream ends

#### Scenario: Error message on invalid operation

- **WHEN** a client subscribes with an invalid document
- **THEN** the server responds with an `error` message carrying the GraphQL errors

#### Scenario: Client complete stops the stream

- **WHEN** a client sends `complete` for an active subscription id
- **THEN** the server stops the stream and releases its resources

### Requirement: Server-Sent Events transport

The integrations layer SHALL offer an SSE transport that streams subscription (or
incremental) results as `text/event-stream` events for clients that cannot use
WebSockets.

#### Scenario: SSE streams events

- **WHEN** a client opens an SSE request for a subscription
- **THEN** each produced result is sent as a discrete SSE `data:` event until the stream completes

### Requirement: Multipart subscription responses

The integrations layer SHALL support `multipart/mixed` incremental responses for
subscriptions where a framework adapter supports streaming HTTP bodies.

#### Scenario: Multipart parts per event

- **WHEN** a subscription is requested over a multipart-capable transport
- **THEN** each event is delivered as a separate multipart part with the result payload
