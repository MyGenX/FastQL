# definition-extensions Specification

## Purpose
Ordered resolver extensions and declarative field permissions.

## Requirements
### Requirement: Ordered field extensions

The framework SHALL allow fields to declare ordered extension objects that wrap resolver execution
and MAY be synchronous or asynchronous.

#### Scenario: Extensions wrap a resolver

- **WHEN** a field declares two extensions
- **THEN** they execute in declaration order around the core resolver and can inspect `Info` and argument values

### Requirement: Field permissions

The framework SHALL allow fields to declare permission classes whose checks run before the resolver
and whose failures become GraphQL field errors.

#### Scenario: Permission denied

- **WHEN** a field permission returns false
- **THEN** the resolver is not called and execution records the permission message using normal null propagation
