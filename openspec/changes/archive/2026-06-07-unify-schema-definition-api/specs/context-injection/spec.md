## ADDED Requirements

### Requirement: Typed resolver info
The executor SHALL provide generic `Info[ContextType, RootType]` containing context, root value, schema, Python and GraphQL field names, path, variables, operation, and selected field nodes.

#### Scenario: Typed info injection
- **WHEN** a resolver declares an `Info` parameter
- **THEN** execution injects the active request metadata and does not expose that parameter as a GraphQL argument

### Requirement: Request-scoped asynchronous dependencies
Dependency providers SHALL be scoped to one execution, SHALL be evaluated at most once per dependency type, and MAY be synchronous or asynchronous.

#### Scenario: Shared dependency
- **WHEN** sibling resolvers request the same registered dependency
- **THEN** its provider runs once and both resolvers receive the same produced value

### Requirement: Per-operation root instances
Each root definition owner SHALL be instantiated once per GraphQL operation and MAY request context or registered dependencies in its constructor.

#### Scenario: Root-local state
- **WHEN** two fields from the same root class execute in one operation
- **THEN** both methods use the same root instance while a later operation receives a new instance
