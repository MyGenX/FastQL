## MODIFIED Requirements

### Requirement: Execute an operation and return a spec-shaped result

The framework SHALL provide an async `execute(schema, query, variable_values=None, context=None, operation_name=None)` entry point that routes parsing, operation selection, validation, and execution through the schema's selected operation backend. It SHALL return a FastQL `ExecutionResult` exposing `data`, `errors`, and `extensions` regardless of backend. String input SHALL use the selected backend's native document model; backend-owned pre-parsed documents SHALL bypass parsing; foreign documents SHALL be rejected. Parse or validation failures SHALL omit executed data and report normalized errors.

#### Scenario: Successful query

- **WHEN** `execute` runs `{ user(id: 1) { id name } }` against either supported backend and the `user` resolver returns a user
- **THEN** the result's `data` is `{"user": {"id": 1, "name": ...}}` and `errors` is empty

#### Scenario: Operation selection

- **WHEN** a backend-owned document defines multiple named operations and `operation_name` selects one
- **THEN** only the named operation is executed by the selected backend

#### Scenario: Parse failure

- **WHEN** `execute` receives malformed source text
- **THEN** the result is unexecuted and contains the selected backend's normalized syntax error

#### Scenario: GraphQL-core native execution options

- **WHEN** a GraphQL-core-backed schema configures middleware, coercion limits, an execution context class, or awaitable detection
- **THEN** native GraphQL-core execution uses those options while returning a FastQL result

### Requirement: Execute normalized field hooks

Execution SHALL invoke field permissions, field extensions, and schema resolve extensions around the normalized FastQL resolver while retaining existing sync/async interoperability, errors, null propagation, and dependency injection under every backend. In GraphQL-core mode, native middleware SHALL wrap the adapted FastQL field resolver without replacing the FastQL hook order inside it.

#### Scenario: Async extension and sync resolver

- **WHEN** an asynchronous FastQL extension wraps a synchronous resolver under either backend
- **THEN** both complete successfully and the field result is completed normally

#### Scenario: Native middleware wraps FastQL hooks

- **WHEN** GraphQL-core middleware and FastQL permission/extension hooks are configured on one field
- **THEN** middleware observes the native field execution while FastQL hooks receive FastQL `Info` and run in their existing order

### Requirement: Configurable error masking

The executor SHALL apply the configured masking policy to normalized backend errors so unexpected resolver failures are either passed through or replaced with a generic message, with original errors preserved for logging. Explicit FastQL or GraphQL-core GraphQL errors SHALL retain their client-facing messages under every backend.

#### Scenario: Unexpected error masked by default

- **WHEN** masking is enabled and an adapted resolver raises an unexpected exception under either backend
- **THEN** the client-facing message is generic while the original error is retained internally

#### Scenario: Explicit GraphQL errors not masked

- **WHEN** a resolver raises an explicit FastQL or GraphQL-core GraphQL error
- **THEN** its message is passed through unchanged regardless of the masking policy
