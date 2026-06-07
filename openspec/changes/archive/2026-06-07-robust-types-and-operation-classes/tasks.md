## 1. Field spec: data vs computed + attribute resolver

- [x] 1.1 In `decorators/field.py`, add a way to tell *data* `FieldSpec`s (no resolver) from *computed* ones (resolver set); ensure `Field(resolver=fn)` used as a class attribute keeps the attribute name and the resolver
- [x] 1.2 Tests: `Field(resolver=fn)` attribute resolves to a computed spec with the attribute name; `Field(description=...)` stays a data spec

## 2. Constructor synthesis

- [x] 2.1 Add `decorators/construct.py`: build `__init__` (positional + keyword, declaration order, honoring defaults) from ordered data fields
- [x] 2.2 Add synthesized `__repr__` and `__eq__`; skip any dunder the class already defines
- [x] 2.3 Tests: positional + keyword construction, defaults honored, generated repr/eq, and user-defined `__init__`/`__eq__` preserved

## 3. @Type field collection update

- [x] 3.1 Rework `decorators/object.py` `_collect_output_fields` to split data fields (annotations + `Field()`-without-resolver) from computed fields (`@Field` methods + `Field(resolver=fn)` attributes)
- [x] 3.2 Invoke constructor synthesis from `@Type` using the ordered data fields; ensure descriptor-backed assignment works
- [x] 3.3 Tests: a `@Type` with data fields + a `@Field` method + a `Field(resolver=fn)` attribute exposes all fields and excludes computed ones from the constructor

## 4. Operation container classes

- [x] 4.1 In `decorators/operations.py`, branch `_operation` on function vs class
- [x] 4.2 Class path: instantiate once (clear error if it needs args), bind `@Field` methods (so `self` is the instance and excluded from args), use `Field(resolver=fn)` attributes directly, and register each as an operation field
- [x] 4.3 Apply the class form to `@Query`, `@Mutation`, and `@Subscription`; keep the function form working
- [x] 4.4 Tests: query class with multiple `@Field` methods; mutation/subscription class forms; undecorated methods ignored; function form still works

## 5. Registry collision detection

- [x] 5.1 In `decorators/registry.py`, make `register_operation` raise a descriptive error on a duplicate field name within the same operation kind
- [x] 5.2 Tests: multiple query classes merge via `build_schema()`; functions + classes compose; duplicate field name raises

## 6. Example refresh, docs, and full suite

- [x] 6.1 Update `examples/hello.py`: remove `User.__init__` (autogen), remove the debug `print`, and convert the free `@Query` functions into a `Queries` class
- [x] 6.2 Refresh the README authoring snippet to show fields-only types and an operation class
- [x] 6.3 Add an end-to-end test exercising the refreshed example (`{ user(id: 1) { id name loudName } ping }`)
- [x] 6.4 Run the full `pytest` suite and confirm back-compat (existing tests stay green)
