## Context

`@Type` (`fastql/decorators/object.py`) turns class annotations into GraphQL fields but generates no
constructor, and `@Query`/`@Mutation`/`@Subscription` (`fastql/decorators/operations.py`) only accept
free functions, registering each into `default_registry.operations[kind]`. `build_schema`
(`fastql/schema_builder.py`) already merges that registry into each root type. This change adds
constructor synthesis and a class-container form for operations, reusing the existing registry/merge
and dependency-injection machinery (`fastql/context.py`'s `injected_parameter_names`).

## Goals / Non-Goals

**Goals**
- Declarative `@Type`: define fields only; get a usable `__init__`/`__repr__`/`__eq__` for free.
- Group operations on a class; compose multiple operation classes into one schema.
- Support `Field(resolver=fn)` attributes (Strawberry-style) for computed fields.
- Full back-compat for function operations and hand-written dunder methods.

**Non-Goals**
- No change to execution, validation, or DI semantics.
- No `@property` auto-exposure; no input-object constructor synthesis; no interface/union changes.

## Decisions

### D1. Distinguish *data* fields from *computed* fields in `FieldSpec`
A `FieldSpec` with no `resolver` is a **data** field (a stored attribute → becomes a GraphQL field
*and* a constructor parameter). A `FieldSpec` with a `resolver` is a **computed** field (resolver-backed
→ GraphQL field only, never a constructor parameter). `_collect_output_fields` is split accordingly:
- data: plain annotations and annotated `Field(...)`-without-resolver;
- computed: `@Field` methods (`cls.__dict__` entries) and annotated `= Field(resolver=fn)` attributes.

`Field(resolver=fn)` used as a class attribute already gets its attribute name via `FieldSpec.__set_name__`;
we ensure the resolver and that name survive (the field name defaults to the attribute name).

### D2. Synthesize the constructor only when absent
A new helper (`fastql/decorators/construct.py`) builds `__init__`, `__repr__`, and `__eq__` from the
ordered **data** fields. Required fields (no default) precede defaulted ones, mirroring dataclass
rules; defaults come from `Field(default=...)` or a plain class-attribute value. Synthesis is skipped
for any dunder the class already defines in its own `__dict__` (so user-written `__init__`/`__eq__` win).
Assignment in the generated `__init__` uses `setattr`, which routes through `FieldSpec.__set__` for
descriptor-backed fields and sets the attribute directly otherwise.

### D3. Operation decorators branch on function vs class
`_operation(kind, target)` checks `isinstance(target, type)`:
- **class** → instantiate once with no args (a clear error if the class requires constructor args),
  then for each `@Field` method bind it to that instance (so `inspect.signature` of the bound method
  drops `self`, and `self` is naturally excluded from GraphQL args) and for each `Field(resolver=fn)`
  attribute use `fn` directly; register each as an operation field (reusing the existing
  argument-derivation that excludes injected params).
- **function** → unchanged.

This keeps the registry shape identical, so `build_schema`'s existing root-merge composes multiple
classes/functions with no change.

### D4. Collision detection at registration
`DecoratorRegistry.register_operation` raises a descriptive error if a field name is already
registered for that operation kind, turning silent last-wins overwrites into an explicit error and
satisfying the "compose multiple containers" requirement.

## Risks / Trade-offs

- **Synthesized `__init__` vs descriptor fields** → assignment via `setattr` routes through
  `FieldSpec.__set__`; covered by tests that read back values and compare equality.
- **Container instantiation side effects** → instantiate once at decoration; a container needing
  constructor args raises a clear error directing users to use defaults or a factory.
- **Ordering of required vs defaulted fields** → enforce dataclass-style ordering; raise a clear error
  if a required field follows a defaulted one (or, more leniently, keep declaration order and rely on
  keyword construction — decided during implementation, leaning on declaration order + keyword-safe).
- **Back-compat** → synthesis is opt-out by defining the dunder; function operations untouched;
  the full existing suite must stay green.

## Migration Plan

Additive and backward compatible. `examples/hello.py` is updated to drop `User.__init__` and use a
`@Query` class; existing user code keeps working. No data migration.

## Open Questions

- Whether to raise on "required field after defaulted field" or simply preserve declaration order and
  rely on keyword construction (leaning: preserve order, keyword-safe; revisit if it surprises).
- Whether container classes should support an injected `Context` at instantiation time (deferred; the
  instance is created without request context for now).
