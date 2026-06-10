## ADDED Requirements

### Requirement: Per-error extensions

GraphQL errors SHALL support an `extensions` mapping that, when present, is
included in the error's formatted output alongside `message`, `locations`, and
`path`.

#### Scenario: Error extensions surfaced

- **WHEN** a resolver raises an error carrying an `extensions` payload (e.g. an error code)
- **THEN** the formatted error includes that `extensions` object

#### Scenario: Backward-compatible omission

- **WHEN** an error has no extensions
- **THEN** the formatted error omits the `extensions` key entirely

### Requirement: Configurable error masking

The executor SHALL support a configurable masking policy that controls whether
unexpected (non-GraphQL) resolver errors are passed through verbatim or replaced
with a generic message, with original errors preserved for logging.

#### Scenario: Unexpected error masked by default

- **WHEN** masking is enabled and a resolver raises an unexpected exception
- **THEN** the client-facing message is generic while the original error is retained internally

#### Scenario: Explicit GraphQL errors not masked

- **WHEN** a resolver raises an explicit `GraphQLError`
- **THEN** its message is passed through to the client unchanged regardless of the masking policy

### Requirement: Subscription execution entrypoint

The execution layer SHALL provide a subscription entrypoint that returns an async
stream of results, distinct from the single-result `execute` path for
queries/mutations.

#### Scenario: Subscription routed to stream

- **WHEN** a subscription operation is submitted to the subscription entrypoint
- **THEN** an async iterator of `ExecutionResult` is returned rather than a single result
