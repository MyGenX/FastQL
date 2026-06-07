## ADDED Requirements

### Requirement: Resolver dependency injection by signature

The executor SHALL inspect each resolver's signature and inject parameters by role: a parameter whose
name matches a GraphQL field argument SHALL receive that coerced argument; a parameter typed as the
parent/source object SHALL receive the parent value; a parameter typed as resolve `info` SHALL receive
field/path/schema metadata; and a parameter typed as `Context` SHALL receive the execution context.
Resolvers SHALL remain plain functions with no required base class, and only declared parameters SHALL
be passed.

#### Scenario: Argument and context injected together

- **WHEN** a resolver is declared `async def user(id: int, ctx: Context) -> User`
- **THEN** the executor passes the coerced `id` argument and the active `Context` instance, and nothing else

#### Scenario: Info injection

- **WHEN** a resolver declares a parameter typed as resolve `info`
- **THEN** the executor passes an info object exposing the current field name, path, and schema

#### Scenario: Unrequested values not passed

- **WHEN** a resolver omits the `Context` parameter
- **THEN** the executor invokes it without a context argument

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
