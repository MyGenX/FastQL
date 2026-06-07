## Why

FastQL currently compiles object-like types and root operations through separate paths, so the same GraphQL field concept behaves differently across `Type`, `Interface`, `Input`, `Query`, `Mutation`, and `Subscription`. Unifying these definitions provides a smaller, more predictable API that supports concise Python annotations and explicit Strawberry-style metadata without duplicating schema-building logic.

## What Changes

- **BREAKING** Replace the split object/operation collectors with one normalized definition pipeline for object, interface, input, and root operation classes.
- **BREAKING** Make decorated root classes and `Schema(query=..., mutation=..., subscription=...)` the canonical assembly API; keep zero-argument `build_schema()` as global discovery convenience.
- Make `Field` the common output-field declaration for annotated values, methods, and resolver-backed attributes, with metadata for names, descriptions, deprecation, defaults, arguments, directives, permissions, and extensions.
- Add `Argument` metadata for `typing.Annotated` and an `Arg(...)` parameter-default shorthand.
- Add schema-level naming configuration with snake-case to camel-case conversion enabled by default.
- Add typed `Info[ContextType, RootType]`, per-operation root instances, and request-scoped sync/async dependency providers.
- Preserve the framework-agnostic, zero-runtime-dependency core.

### Non-goals / Out of Scope

- HTTP transports, framework adapters, federation, dataloaders, persisted queries, and subscription transport protocols.
- Full API compatibility with Strawberry or compatibility shims for the old FastQL operation-function authoring API.
- User-defined executable GraphQL directive implementations beyond carrying applied directive metadata in schema definitions.

## Capabilities

### New Capabilities

- `definition-extensions`: Ordered field extensions and permission hooks for sync and async resolvers.

### Modified Capabilities

- `schema-definition`: Unify decorators, fields, arguments, constructors, root definitions, and naming behavior.
- `schema-building`: Add canonical `Schema` assembly, configurable naming, and merged root discovery.
- `context-injection`: Add generic resolve info, per-operation roots, and request-scoped async-capable dependencies.
- `query-execution`: Run field extensions and permissions around resolver invocation.
- `type-system`: Carry applied directives and normalized field metadata in the schema IR.
- `introspection`: Reflect normalized names, defaults, descriptions, deprecations, and directives consistently.

## Impact

The public decorator exports, schema constructor, schema builder, context API, executor invocation, type IR, examples, README, and decorator/context/schema tests change. Existing schemas using standalone `@Query` functions or relying on preserved snake_case GraphQL names require migration. No runtime dependency or transport-layer change is introduced.
