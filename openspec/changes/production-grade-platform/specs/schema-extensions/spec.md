## ADDED Requirements

### Requirement: Schema extension lifecycle hooks

FastQL SHALL support `SchemaExtension` objects registered on a schema that are
invoked around each phase of operation handling: `on_operation`, `on_parse`,
`on_validate`, and `on_execute`. Each hook SHALL be able to run code before and
after its phase (e.g. via a generator/`yield` or paired enter/exit methods).

#### Scenario: Hooks fire in phase order

- **WHEN** an operation is processed with a registered extension
- **THEN** `on_operation` begins first, then `on_parse`, `on_validate`, `on_execute` run within it, and each completes in reverse nesting order

#### Scenario: Multiple extensions compose

- **WHEN** two extensions A and B are registered in order
- **THEN** A wraps B for each phase, and both observe begin/end around the phase

### Requirement: Resolver wrapping hook

`SchemaExtension` SHALL provide a `resolve` hook that wraps every field resolver
call, receiving the next callable plus `source`, `info`, and arguments, allowing
extensions to time, short-circuit, or transform resolution.

#### Scenario: Resolve wrapper observes every field

- **WHEN** an extension defines `resolve` and a query selects multiple fields
- **THEN** the wrapper is invoked once per resolved field and may call `next_` to continue

#### Scenario: Extension can attach response extensions

- **WHEN** an extension produces metadata via a `get_results` hook
- **THEN** that metadata is merged into the `ExecutionResult.extensions` mapping

### Requirement: Async and sync extension support

Extension hooks SHALL support both synchronous and asynchronous implementations,
consistent with FastQL's async-first executor.

#### Scenario: Async hook awaited

- **WHEN** an extension hook is an async generator or coroutine
- **THEN** the executor awaits it correctly within the operation lifecycle
