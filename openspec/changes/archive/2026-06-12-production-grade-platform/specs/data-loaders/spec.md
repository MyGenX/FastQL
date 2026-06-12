## ADDED Requirements

### Requirement: Batched data loading

FastQL SHALL provide a `DataLoader` utility that coalesces individual key lookups
made within a single execution into batched calls to a user-supplied async batch
function, returning results in the same order as the requested keys.

#### Scenario: Keys requested in the same tick are batched

- **WHEN** a resolver calls `loader.load(k1)` and a sibling resolver calls `loader.load(k2)` during the same execution
- **THEN** the batch function is invoked once with `[k1, k2]` and each `load` call resolves to its corresponding result

#### Scenario: load_many returns aligned results

- **WHEN** a resolver awaits `loader.load_many([k1, k2, k3])`
- **THEN** it returns a list of three results positionally aligned to the keys

#### Scenario: Batch size honored

- **WHEN** a loader is configured with `max_batch_size=2` and three keys are requested in one tick
- **THEN** the batch function is invoked in chunks of at most two keys

### Requirement: Per-key caching and deduplication

A `DataLoader` SHALL cache results by key for its lifetime so repeated `load(k)`
calls for the same key resolve to the same result without re-invoking the batch
function, and SHALL expose `clear(key)`, `clear_all()`, and `prime(key, value)`.

#### Scenario: Duplicate keys deduplicated

- **WHEN** `load(k1)` is called twice before the batch resolves
- **THEN** `k1` appears once in the batch function call and both awaits return the same value

#### Scenario: Cache invalidation

- **WHEN** `clear(k1)` is called after `k1` was loaded
- **THEN** the next `load(k1)` re-invokes the batch function for `k1`

### Requirement: Request-scoped loader access

FastQL SHALL allow loaders to be scoped per request and accessed from resolvers
via the `Context` and/or `Info`, so that caching does not leak across requests.

#### Scenario: Loader reachable from a resolver

- **WHEN** a loader is registered on the request context and a resolver retrieves it via `info`/`context`
- **THEN** the resolver can call `load`/`load_many` and benefits from batching within that request

#### Scenario: Errors in batch function propagate per key

- **WHEN** the batch function returns an exception (or raises) for a particular key
- **THEN** the corresponding `load` call rejects with that error while other keys resolve normally
