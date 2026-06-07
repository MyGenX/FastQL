## Context

FastQL is a greenfield Python GraphQL framework; the repository currently holds only OpenSpec
scaffolding. This change defines the **core engine and authoring surface**: a code-first, decorator
API that compiles to a hand-built type-system IR, executed by an async-first engine with a built-in
dependency-injection/context layer — all independent of any web framework. Transport adapters
(ASGI, FastAPI, Django, Flask) and a subscription wire protocol are intentionally deferred to later
changes that consume this core's public API.

Constraints driving the design:
- **Custom engine, zero runtime dependencies** — we own the lexer, parser, validator, and executor.
- **Python 3.11+** — modern typing (`X | None`, builtin generics, `inspect`/`typing` introspection).
- **Web-framework agnostic** — the core never imports an HTTP framework; it speaks Python values in
  and `ExecutionResult` out.
- **Primitive, ergonomic authoring** — type hints drive the schema; decorators are thin metadata.

## Goals / Non-Goals

**Goals:**
- A layered, single package (`fastql`) where each layer depends only on the ones below it, so layers
  are independently testable (lex/parse without a schema; build a schema without executing).
- Decorators (`@Type`, `@Input`, `@Interface`, `@Enum`, `@Union`, `@Scalar`, `@Query`, `@Mutation`,
  `@Subscription`, `@Field`) that register metadata only, plus a `Field()` descriptor for overrides.
- A `build_schema()` that resolves forward/circular references via thunks and validates completeness.
- An async-first executor supporting mixed `async`/`sync` resolvers, spec-faithful coercion, error
  handling, and partial-data/null-propagation semantics.
- A signature-driven DI/context layer so resolvers stay plain functions.
- Built-in introspection so external tooling works once a transport exists.

**Non-Goals:**
- No HTTP server, ASGI/WSGI handler, or web-framework binding.
- No persistence, ORM integration, DataLoader/batching, or caching.
- No subscription wire protocol (the decorator and async-generator path are defined; transport later).
- Not aiming for full GraphQL validation-rule coverage in v1 — a pragmatic, growable subset.

## Decisions

### D1. Build a custom engine instead of wrapping `graphql-core`
Owning the lexer→parser→validator→executor pipeline gives FastQL the "unique structural design" the
project wants, zero dependencies, and freedom to shape error/DI semantics. **Alternative considered:**
compiling decorators down to a `graphql-core` schema (what Strawberry/Graphene do) — faster to ship
and spec-complete, but couples us to its execution model and value semantics. **Trade-off accepted:**
more code and the burden of spec fidelity, mitigated by layering and heavy unit tests, and by scoping
validation to a growable subset.

### D2. Layered package with a thin decorator surface over a type-system IR
Decorators record metadata into a `TypeRegistry`; `build_schema()` compiles that into the IR the
executor consumes. This keeps authoring concerns (Python classes, hints) separate from runtime
concerns (types, coercion, resolution). **Alternative:** decorators that eagerly construct IR objects —
rejected because eager construction cannot express forward/circular references cleanly.

### D3. Type hints drive types; `Field()` overrides
GraphQL types are inferred from annotations (`int→Int`, `str→String`, `bool→Boolean`, `float→Float`,
an `ID` marker, `X | None`/`Optional`→nullable, `list[X]`→`List`, `Enum`→enum, registered classes and
string forward refs→their types; a bare hint→`NonNull`). `Field(...)` is both an attribute default
(to attach description/deprecation/name/custom type) and an `@Field` method decorator for computed
fields. **Alternative:** explicit type arguments in every decorator — rejected as too verbose for the
"primitive usage" goal, but retained as the override path for cases hints cannot express.

### D4. Forward references resolved via lazy thunks at build time
Annotations referencing not-yet-defined types (including string forward refs like `"User"`) are stored
as zero-argument thunks in the registry and resolved during `build_schema()`. This is the mechanism
that makes recursive and mutually-referential types work without import-order constraints.

### D5. Async-first executor with sync adaptation
The executor runs on `asyncio` and resolves sibling fields concurrently via `asyncio.gather`. Each
resolver is classified once (coroutine function vs plain function); plain functions are awaited inline
(or offloaded if they would block), so users freely mix `async def` and `def`. **Alternative:** a
sync-only core with async bolted on later — rejected because retrofitting async through the executor is
far costlier than designing for it now.

### D6. Signature-driven dependency injection (the "unique" wiring)
At resolve time the executor inspects each resolver's signature (`inspect.signature` + annotations) and
binds parameters by role: names matching GraphQL field arguments receive coerced args; a parameter
typed `Context` receives the execution context; a parameter typed as resolve `info` receives field
metadata; the parent/source object binds to a designated parameter; and parameters typed as a
registered dependency are produced by a provider from the active context. Resolvers need no base class.
Signature classification is cached per resolver to avoid per-call reflection cost. **Alternative:** a
fixed `(parent, info, **args)` resolver signature like reference implementations — rejected as less
ergonomic and less distinctive than typed injection.

### D7. Spec-faithful error and null-propagation model
Field errors are captured as `GraphQLError` with `message`, `locations`, and `path`; the field becomes
null and the null propagates to the nearest nullable ancestor per the GraphQL spec, while unaffected
fields keep resolving. Execution always returns an `ExecutionResult{ data, errors, extensions }`.

### D8. Introspection implemented as built-in meta-fields
`__schema`, `__type`, and `__typename` are wired into the schema/executor so standard tooling and
codegen work as soon as a transport is added — satisfying the "follow GraphQL best practice" goal.

### Data flow
`query string → Lexer → Parser → Document AST → (validate against Schema) → select operation →
collect fields (fragments, @skip/@include) → coerce args/variables → resolve (DI + async) →
coerce outputs → ExecutionResult{data, errors}`. The `Schema` IR is produced once by
`build_schema()` from the `TypeRegistry`.

## Risks / Trade-offs

- **Spec-fidelity burden of a hand-built engine** → Mitigate with a layered design, exhaustive unit
  tests per layer, conformance-style tests derived from each spec scenario, and an explicitly *growable*
  validation subset rather than claiming full coverage in v1.
- **Coercion and null-propagation edge cases are subtle** → Centralize all coercion in one `values`
  module and null-propagation in the executor; test nullable/non-null and list nesting matrices directly.
- **Reflection cost / fragility of signature-based DI** → Cache the per-resolver injection plan; fall
  back to clear errors when a parameter cannot be classified (unknown type, ambiguous name).
- **Forward-reference resolution failures surface late** → `build_schema()` performs a completeness
  pass that raises descriptive errors (missing type, name collision, unsatisfied interface) before any
  query runs, turning late runtime failures into build-time failures.
- **Async-first excludes a pure-sync embedding** → Acceptable for the core; a thin sync wrapper over
  `execute` can be added later if a synchronous transport needs it.
- **Scope creep toward transport** → Enforce the boundary: the core must not import any web framework;
  transports are separate OpenSpec changes consuming `build_schema`/`execute`.

## Migration Plan

Greenfield — no existing system to migrate. Rollout is purely additive: introduce the `fastql`
package and its tests. There is no production surface to roll back; reverting means removing the new
package. Subsequent changes (transport adapters, subscriptions, batching) build on the stable public
API established here (`build_schema`, `execute`, the decorators, `Field`, `Context`, built-in scalars).

## Open Questions

- Final name/spelling of the `ID` marker and the custom-scalar registration ergonomics (`@Scalar`
  signature) — to be settled during P2/P3 implementation.
- Whether sync resolvers that block should be auto-offloaded to a thread pool by default or only on
  opt-in — default chosen during P6, leaning toward inline-await with documented guidance.
- Depth/scope of the v1 validation rule set beyond the must-have rules listed in `query-validation`.
