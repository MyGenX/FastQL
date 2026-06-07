# context-injection Specification

## Purpose
Resolver dependency injection by signature and the per-request Context, including registered dependency providers.
## Requirements
### Requirement: Resolver dependency injection by signature

The executor SHALL inspect each resolver's signature and inject parameters by role: a parameter whose
name matches a GraphQL field argument SHALL receive that coerced argument; a parameter typed as the
parent/source object SHALL receive the parent value; a parameter typed as generic `Info` SHALL receive
request and field metadata; and a parameter typed as `Context` SHALL receive the execution context.
Resolvers SHALL remain plain functions with no required base class, and only declared parameters SHALL
be passed.

#### Scenario: Argument and context injected together

- **WHEN** a resolver is declared `async def user(id: int, ctx: Context) -> User`
- **THEN** the executor passes the coerced `id` argument and the active `Context` instance, and nothing else

#### Scenario: Info injection

- **WHEN** a resolver declares a parameter typed as resolve `info`
- **THEN** the executor passes an `Info` object exposing the current Python and GraphQL field names, path, schema, context, root value, variables, operation, and selected fields

#### Scenario: Unrequested values not passed

- **WHEN** a resolver omits the `Context` parameter
- **THEN** the executor invokes it without a context argument

### Requirement: Typed resolver info

The executor SHALL provide generic `Info[ContextType, RootType]` containing context, root value,
schema, Python and GraphQL field names, path, variables, operation, and selected field nodes.

#### Scenario: Typed info injection

- **WHEN** a resolver declares an `Info` parameter
- **THEN** execution injects the active request metadata and does not expose that parameter as a GraphQL argument

### Requirement: Context value and dependency providers

The framework SHALL allow a caller to supply a `context` value to `execute`, accessible to every
resolver as the `Context`. The framework SHALL provide a mechanism to register dependency providers so
that a resolver parameter typed as a registered dependency receives a value produced from the active
context (for example an auth principal or a database session).

#### Scenario: Context value reaches resolvers

- **WHEN** `execute(..., context=ctx)` is called
- **THEN** every resolver that declares a `Context` parameter receives `ctx`

#### Scenario: Registered dependency resolved from context

- **WHEN** a dependency provider for `CurrentUser` is registered and a resolver declares a `CurrentUser` parameter
- **THEN** the executor invokes the provider with the active context and passes its result to the resolver

### Requirement: Request-scoped asynchronous dependencies

Dependency providers SHALL be scoped to one execution, SHALL be evaluated at most once per dependency
type, and MAY be synchronous or asynchronous.

#### Scenario: Shared dependency

- **WHEN** sibling resolvers request the same registered dependency
- **THEN** its provider runs once and both resolvers receive the same produced value

### Requirement: Per-operation root instances

Each root definition owner SHALL be instantiated once per GraphQL operation and MAY request context
or registered dependencies in its constructor.

#### Scenario: Root-local state

- **WHEN** two fields from the same root class execute in one operation
- **THEN** both methods use the same root instance while a later operation receives a new instance

### Requirement: Request-aware web context

Web-framework adapters SHALL create a per-request `HTTPContext` that extends `Context` and exposes the native framework request, the host application when available, mutable request state, and framework-neutral response controls. The integration context SHALL remain dependency-free and SHALL NOT require importing a framework type.

#### Scenario: Native request reaches a resolver

- **WHEN** a GraphQL operation executes through a web-framework adapter and a resolver requests the active context
- **THEN** the resolver can access the native framework request from that request's `HTTPContext`

#### Scenario: Middleware state reaches a resolver

- **WHEN** host middleware stores authentication or request data on the native request before GraphQL execution
- **THEN** the resolver can reach that data through the native request in the context

### Requirement: Unified adapter context factory

Every web-framework adapter SHALL accept a context factory with the same contract. The adapter SHALL pass the newly created `HTTPContext` to the factory, SHALL support synchronous and asynchronous factories, and SHALL use the factory's returned context for resolver and `Info.context` injection. Returning no replacement SHALL retain the provided `HTTPContext`.

#### Scenario: Asynchronous context enrichment

- **WHEN** an async context factory receives the request context, adds request-scoped state, and returns it
- **THEN** resolvers receive the enriched context after the factory completes

#### Scenario: Custom typed context replacement

- **WHEN** a context factory returns an application-defined `Context` subclass
- **THEN** that object becomes the execution context for the operation

### Requirement: Request-scoped response controls

The web context SHALL provide framework-neutral response controls for adding response headers during execution, and each adapter SHALL apply those controls to its native response without sharing state between requests.

#### Scenario: Resolver adds a response header

- **WHEN** request-scoped code adds a header through the context response controls
- **THEN** the final native framework response contains that header only for the active request
