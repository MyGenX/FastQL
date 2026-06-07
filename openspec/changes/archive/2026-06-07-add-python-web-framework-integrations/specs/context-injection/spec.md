## ADDED Requirements

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

