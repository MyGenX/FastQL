# query-execution Specification

## Purpose
Async-first execution of operations: field collection, value coercion, error handling, and null propagation.
## Requirements
### Requirement: Execute an operation and return a spec-shaped result

The framework SHALL provide an async `execute(schema, query, variable_values=None, context=None,
operation_name=None)` entry point that parses (when given a string), validates, and executes the
selected operation. It SHALL return an `ExecutionResult` exposing `data`, `errors`, and `extensions`.
When the document fails to parse or validate, `data` SHALL be absent and `errors` SHALL describe the
failure.

#### Scenario: Successful query

- **WHEN** `execute` runs `{ user(id: 1) { id name } }` against a schema whose `user` resolver returns a user
- **THEN** the result's `data` is `{"user": {"id": 1, "name": ...}}` and `errors` is empty

#### Scenario: Operation selection

- **WHEN** a document defines multiple named operations and `operation_name` selects one
- **THEN** only the named operation is executed

#### Scenario: Parse failure

- **WHEN** `execute` is given a malformed query string
- **THEN** the result has no `data` and `errors` contains the syntax error

### Requirement: Field resolution, coercion, and concurrency

Execution SHALL collect fields (honoring fragments and the `@skip`/`@include` directives), coerce
argument and variable input values to their declared types, invoke each field's resolver, and coerce
resolver outputs to their declared GraphQL types. Sibling fields SHALL be resolved concurrently using
`asyncio`. Both `async def` and plain `def` resolvers SHALL be supported.

#### Scenario: Sync and async resolvers together

- **WHEN** a selection set mixes an `async def` resolver and a plain `def` resolver
- **THEN** both resolve correctly and their values appear in `data`

#### Scenario: Skip directive

- **WHEN** a field carries `@skip(if: true)`
- **THEN** that field is omitted from the result

#### Scenario: Argument coercion

- **WHEN** a field argument declared as `Int!` is provided via a variable whose value is `5`
- **THEN** the resolver receives the integer `5`

### Requirement: Error handling and partial data

When a resolver raises an error or returns an invalid value, execution SHALL record a `GraphQLError`
carrying the field `path` and source `location`, set the field's value to null, and propagate the
null according to nullability: a null in a non-null position SHALL propagate to the nearest nullable
parent. Execution SHALL continue resolving unaffected fields and return both partial `data` and the
collected `errors`.

#### Scenario: Resolver raises on a nullable field

- **WHEN** a resolver for a nullable field raises an exception
- **THEN** that field is null in `data`, sibling fields still resolve, and `errors` contains an entry with the field's path

#### Scenario: Null propagation through non-null field

- **WHEN** a non-null field resolves to null (or its resolver errors)
- **THEN** the null propagates to the nearest nullable ancestor and a corresponding error is recorded

### Requirement: Execute normalized field hooks

Execution SHALL invoke field permissions and extensions around the normalized resolver while retaining
existing sync/async interoperability, errors, and null propagation.

#### Scenario: Async extension and sync resolver

- **WHEN** an asynchronous extension wraps a synchronous resolver
- **THEN** both complete successfully and the field result is completed normally

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

