## Why

Defining a FastQL type is more ceremony than it should be: `@Type` reads annotations into GraphQL
fields but generates no constructor, so to actually *create* instances users must hand-write
`__init__` (as `examples/hello.py`'s `User` does). And root operations can only be free functions —
there is no way to group related queries on a class or to compose several query classes into one
schema. This change makes type definitions declarative ("just a name and a set of fields") by
auto-generating constructors, and lets the operation decorators accept a class of methods that merge
into the schema.

## What Changes

- **Auto-generated constructors**: `@Type` classes that don't define their own `__init__` get a
  synthesized dataclass-style `__init__` (positional + keyword, honoring defaults) plus `__repr__`
  and `__eq__`. Users define only fields; `User(1, "Ada")` / `User(id=1, name="Ada")` just work.
- **Resolver-backed fields via `Field(resolver=...)`**: an annotated attribute
  `books: list[Book] = Field(resolver=get_books)` registers a computed field whose resolver is the
  given function (Strawberry-style), in addition to the existing `@Field` method form.
- **Operation container classes**: `@Query`, `@Mutation`, and `@Subscription` may decorate a **class**.
  Its `@Field`-marked methods and its `Field(resolver=...)` attributes become root fields; `@Field`
  methods are bound to a single class instance so `self` is available and hidden from GraphQL args.
  Plain undecorated methods are ignored. The existing function form still works.
- **Composing multiple operation classes**: several `@Query` (and `@Mutation`/`@Subscription`)
  classes/functions merge into one root type at `build_schema()`; a duplicate field name across them
  raises a descriptive error.
- Non-goals: no change to the execution engine, validation, or dependency injection; `@property` is
  **not** auto-exposed as a field; input-object constructors and interface/union semantics are
  unchanged.

## Capabilities

### New Capabilities
<!-- None — this change extends existing capabilities. -->

### Modified Capabilities
- `schema-definition`: add auto-generated object constructors, `Field(resolver=...)` resolver-backed
  fields, and the operation-container-class form (extending the operation decorators).
- `schema-building`: composing root operation types from multiple operation containers, with
  duplicate-field-name detection.

## Impact

- **Code**: `fastql/decorators/field.py` (data vs computed `FieldSpec`, attribute-form `Field(resolver=)`),
  `fastql/decorators/object.py` (field-collection split + constructor synthesis), a new constructor
  helper (e.g. `fastql/decorators/construct.py`), `fastql/decorators/operations.py` (class containers),
  and `fastql/decorators/registry.py` (duplicate-field collision check). `fastql/schema_builder.py`
  already merges registered operations and needs no structural change.
- **Examples/docs**: `examples/hello.py` updated to drop the manual `User.__init__` and use a query
  class; README authoring snippet refreshed.
- **Dependencies**: none added (stdlib only).
- **Back-compat**: existing free-function operations and hand-written `__init__`/`__eq__` continue to
  work unchanged; synthesis is skipped when the user defines those methods.
