## 1. Unified Definition Model

- [x] 1.1 Add normalized definition, field, argument, directive, permission, and extension metadata types.
- [x] 1.2 Replace object and operation collection with one compiler for Type, Interface, Input, Query, Mutation, and Subscription classes.
- [x] 1.3 Add pytest coverage for annotation-only, Field, resolver attribute, method, input, interface, and operation definitions.

## 2. Schema Assembly And Naming

- [x] 2.1 Add SchemaConfig and canonical Schema construction from explicit decorated roots.
- [x] 2.2 Update build_schema discovery to merge root classes and detect final-name collisions.
- [x] 2.3 Add pytest coverage for camel casing, disabled conversion, explicit overrides, explicit roots, and discovered roots.

## 3. Context And Execution

- [x] 3.1 Add generic Info metadata and deterministic resolver/constructor parameter classification.
- [x] 3.2 Add per-operation root instances and request-scoped sync/async dependency caching.
- [x] 3.3 Add ordered extension and permission execution around field resolvers.
- [x] 3.4 Add pytest coverage for typed info, root lifecycle, asynchronous dependencies, permissions, extensions, and error propagation.

## 4. Metadata And Public API

- [x] 4.1 Propagate normalized metadata through IR, SDL, and introspection.
- [x] 4.2 Update package exports, README, and examples to the new canonical API.
- [x] 4.3 Run the complete pytest suite and resolve regressions.
