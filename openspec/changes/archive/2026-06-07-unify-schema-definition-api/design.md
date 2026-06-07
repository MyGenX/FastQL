## Context

FastQL has two schema authoring pipelines: object-like decorators collect annotated class attributes, while operation decorators immediately register root fields. Both eventually produce the same `Field` IR but differ in naming, argument handling, resolver binding, lifecycle, and metadata. The project is pre-1.0, so this change intentionally replaces that split API instead of maintaining adapters.

## Goals / Non-Goals

**Goals:**
- Compile every class-shaped GraphQL definition through one collector and normalized metadata model.
- Support annotation-only declarations and explicit Strawberry-style `Field`, `Argument`, and `Arg` declarations.
- Make explicit `Schema` roots canonical while retaining modular root auto-discovery.
- Provide deterministic naming, context, dependency, permission, and extension behavior.

**Non-Goals:**
- No transport, federation, dataloader, or framework-integration work.
- No compatibility layer for standalone operation decorators.
- No general executable custom-directive engine.

## Decisions

### One definition compiler

All class decorators attach a `DefinitionSpec` describing kind, GraphQL name, description, interfaces, and Python class. A shared collector turns annotations and `FieldSpec` values into normalized fields. Output definitions produce `Field`; input definitions produce `InputField`; root definitions remain object definitions tagged with their operation kind. This avoids the current duplicated collectors while retaining distinct GraphQL input/output validation.

### Field and argument metadata

`Field` is the single output-field declaration and supports attributes, methods, and `resolver=`. `Argument` is immutable metadata intended for `Annotated[T, Argument(...)]`; `Arg(...)` is equivalent metadata usable as a parameter default. Plain annotations remain the shortest form. Defaults use an explicit missing sentinel, and `default` and `default_factory` are mutually exclusive.

### Naming is finalized at schema build

Collectors preserve Python names and explicit GraphQL overrides. `SchemaConfig(auto_camel_case=True)` finalizes field and argument names during schema construction, allowing the same decorated definitions to be built with different naming policies. Explicit `name=` always wins.

### Explicit and discovered schema assembly

`Schema(query=Query, ...)` accepts decorated root classes and compiles them with the selected config. `build_schema()` discovers registered root definitions and merges distinct fields by operation kind. Duplicate final GraphQL names are errors. The low-level IR schema remains available internally as `Schema`'s built representation.

### Per-operation root lifecycle

Root fields retain an owner class and unbound resolver. At execution start, each root owner is instantiated once for that operation and reused by its fields. A constructor may accept injected context, typed dependencies, or no arguments. This avoids schema-wide mutable singletons and decoration-time side effects.

### Typed info and request dependencies

`Info[ContextType, RootType]` replaces `ResolveInfo` as the primary type while retaining `ResolveInfo` as an alias. It includes Python and GraphQL field names, path, parent type, schema, context, root value, variables, operation, and selected field nodes. Dependency providers are stored on the schema when built; each provider is evaluated at most once per execution and may return an awaitable.

### Extensions and permissions

Every field carries ordered extension objects. Resolution wraps the core resolver from last to first through `resolve(next_, source, info, **kwargs)`, awaiting results as needed. Permission classes implement `has_permission(source, info, **kwargs)` and optional `message`; failed permissions raise `GraphQLError`. Permissions are adapted into the same extension chain.

## Risks / Trade-offs

- [Decorated global discovery remains process-global] -> Explicit `Schema` roots are canonical and registry clearing remains available for tests and dynamic applications.
- [Build-time renaming mutates shared IR] -> Build fresh IR objects from immutable-ish definition specs for each schema.
- [Async providers cannot be resolved while building argument metadata] -> Providers run only during execution and injected parameters are classified by their registered types.
- [Large breaking surface] -> Update all examples, exports, and tests in the same change and document the new canonical forms.

## Migration Plan

Replace standalone operation functions with decorated root classes, construct schemas with `Schema(query=...)`, change clients expecting snake_case GraphQL names or disable `auto_camel_case`, and replace custom `ResolveInfo` annotations with `Info` where generic typing is useful. The old low-level schema container is retained under an internal/IR name so the executor and existing direct-IR tests can migrate incrementally.

## Open Questions

None. The implementation choices above are fixed for this change.
