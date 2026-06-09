# Advanced authoring cookbook

These independent schemas demonstrate the Phase 2 authoring features without changing
the contracts of the shared [`examples.app`](../app) integration showcase.

| Recipe | What it demonstrates |
| --- | --- |
| [`generics.py`](generics.py) | One `Page[T]` template synthesized as `UserPage` and `PostPage` |
| [`relay.py`](relay.py) | Relay `Node`, opaque global IDs, node resolution, and cursor connections |
| [`schema_metadata.py`](schema_metadata.py) | Custom directives, private/external fields, and enum value metadata |

Each module exports its own `schema`. Keeping Relay separate is important: the main
showcase already has an application-specific `Node` interface with `id: Int!`, while
Relay requires a global `id: ID!`.

## Run the tour

```bash
python -m examples.advanced.demo
```

The metadata recipe prints SDL because applied directives, external fields, and enum
deprecations are schema-level behavior. Its `Product.internal_code` field remains usable
inside Python resolvers but is absent from GraphQL SDL and introspection.

