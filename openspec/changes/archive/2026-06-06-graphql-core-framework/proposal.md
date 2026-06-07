## Why

Python's GraphQL ecosystem forces a trade-off: schema-first tooling drifts from runtime code, and the
popular code-first libraries are each welded to assumptions about a particular web framework or rely on
the aging `graphql-core` engine. FastQL exists to provide a **code-first, decorator-driven** GraphQL
framework with its **own purpose-built engine** and a **web-framework-agnostic core** — so the same
schema definition can later be served over FastAPI, Django, Flask, raw ASGI, or anything else via
pluggable transport adapters. This first change establishes that core.

## What Changes

- Introduce the `fastql` package: a zero-runtime-dependency, Python 3.11+ GraphQL core.
- Add a hand-built GraphQL **language front-end**: `Source` → lexer → recursive-descent parser → AST,
  with syntax errors that carry source locations.
- Add a **type-system IR**: object/interface/union/enum/input/scalar definitions, `NonNull`/`List`
  wrappers, built-in scalars (`Int`, `Float`, `String`, `Boolean`, `ID`), and a `Schema` container.
- Add the **decorator API** — `@Type`, `@Input`, `@Interface`, `@Enum`, `@Union`, `@Scalar`, `@Query`,
  `@Mutation`, `@Subscription`, `@Field` — plus a `Field(...)` descriptor. Field/argument types are
  inferred from **Python type hints**, with `Field(...)` as an optional override for description,
  deprecation, custom name, or custom scalar.
- Add a **registry + `build_schema()`** that compiles decorated definitions into the IR, resolving
  forward/circular references via thunks and validating schema completeness.
- Add a **minimal query validator** that checks an operation against the schema.
- Add an **async-first executor** (`execute(...)`) supporting both `async def` and `def` resolvers,
  concurrent field resolution, input/output coercion, and spec-faithful `{ data, errors }` results
  with partial-data semantics.
- Add a built-in **context / dependency-injection** layer: resolvers stay plain functions, and the
  executor injects GraphQL arguments, parent object, resolve `info`, the `Context`, and registered
  dependencies based on each resolver's signature.
- Add **introspection** meta-fields (`__schema`, `__type`, `__typename`).
- Non-goals (explicit): **no HTTP/transport layer**, no specific web-framework binding, no persistence,
  no DataLoader/batching, and **no subscription wire protocol** in this change (the `@Subscription`
  decorator and async-generator execution path are defined, but transport is deferred).

## Capabilities

### New Capabilities
- `language-parsing`: Lex and parse a GraphQL document string into an AST; report syntax errors with source locations.
- `type-system`: The schema IR — type definitions, `NonNull`/`List` wrappers, built-in scalars, and the `Schema` container.
- `schema-definition`: The decorator surface (`@Type`/`@Input`/`@Interface`/`@Enum`/`@Union`/`@Scalar`/`@Query`/`@Mutation`/`@Subscription`/`@Field` + `Field()`) and type-hint-to-IR resolution.
- `schema-building`: `build_schema(...)` — compile registered definitions into a validated `Schema`, resolving forward/circular references.
- `query-validation`: Validate a parsed operation against the schema before execution.
- `query-execution`: Async-first execution with coercion, error/partial-data semantics, and an `ExecutionResult`.
- `context-injection`: Resolver-signature dependency injection, the `Context` object, and dependency providers.
- `introspection`: `__schema`, `__type`, and `__typename` meta-fields.

### Modified Capabilities
<!-- None — this is the first change in a greenfield project; no existing specs in openspec/specs/. -->

## Impact

- **New code**: the entire `fastql/` package (`language/`, `types/`, `decorators/`, `registry.py`,
  `schema_builder.py`, `validation/`, `execution/`, `context.py`, `introspection.py`, `__init__.py`).
- **Tooling/build**: `pyproject.toml` (package `fastql`, Python 3.11+), dev dependencies `pytest` and
  `pytest-asyncio`, and a `tests/` suite.
- **Dependencies**: zero runtime dependencies by design (the engine is hand-built).
- **Public API surface**: `fastql.build_schema`, `fastql.execute`, the decorators, `Field`, `Context`,
  and the built-in scalars become the stable contract that future transport adapters depend on.
- **Future changes** (out of scope here): HTTP/ASGI transport, FastAPI/Django/Flask adapters,
  subscription wire protocol, and DataLoader-style batching all build on top of this core.
