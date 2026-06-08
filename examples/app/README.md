# `examples.app` — the FastQL showcase schema

A small **blog / community** API that exercises the whole FastQL authoring surface in
one well-structured, framework-agnostic package. The per-framework projects under
[`examples/projects`](../projects) all mount **this exact schema** — that reuse is the
proof that the core integrates into any web framework with only a few lines of glue.

## Run it

```bash
# Standalone tour (queries + mutation + subscription, no web framework)
python -m examples.app.demo

# In the browser via the built-in dev server
python -m fastql serve examples.app:schema --context examples.app:make_context

# Export the SDL
python -m fastql export-schema examples.app:schema
```

## File map — where each GraphQL concept lives

| Concept | File | What it shows |
| --- | --- | --- |
| `@Scalar` | [`scalars.py`](scalars.py) | `DateTime` with `serialize` / `parse_value` / `parse_literal` |
| `@Enum` | [`enums.py`](enums.py) | `Role`, `PostStatus` from `enum.Enum` |
| `@Interface` | [`interfaces.py`](interfaces.py) | `Node`, implemented by every object type |
| `@Type` + `@Union` | [`types.py`](types.py) | `User` / `Post` / `Comment`; `SearchResult = User \| Post`; computed fields |
| `@Input` | [`inputs.py`](inputs.py) | `CreatePostInput`, `PostFilter` (incl. a scalar as input) |
| `DataLoader` | [`loaders.py`](loaders.py) | batched relationship loads via `get_loader` (no N+1) |
| `@Query` | [`queries.py`](queries.py) | `node`, `user(s)`, `posts(filter)`, `search`, `me`, `serverTime` |
| `@Mutation` | [`mutations.py`](mutations.py) | `createPost`, `publishPost`, `addComment` |
| `@Subscription` | [`subscriptions.py`](subscriptions.py) | `postAdded`, `commentAdded` over pub/sub |
| `BasePermission` | [`permissions.py`](permissions.py) | `IsAuthenticated`, `IsAdmin` on mutations |
| `FieldExtension` | [`mutations.py`](mutations.py) | `AuditLog` wrapping a resolver |
| `SchemaExtension` | [`extensions.py`](extensions.py) | `Timing`, `ResolverCount` → `result.extensions` |
| Dependency injection | [`providers.py`](providers.py) | `Clock` injected by type via `register_dependency` |
| Context | [`context.py`](context.py) | `AppContext` carrying the signed-in user |
| Data | [`data.py`](data.py) | in-memory `Store` + `reseed()` |
| Pub/Sub | [`pubsub.py`](pubsub.py) | tiny async fan-out backing subscriptions |
| Assembly | [`schema.py`](schema.py) | `Schema(query=…, mutation=…, subscription=…, extensions=[…])` |

## Subscriptions caveat

FastQL's live subscription **transport** (WebSocket / SSE) is not implemented yet, so the
framework projects serve queries and mutations over HTTP but **not** subscriptions.
Subscriptions are demonstrated through the core `subscribe()` API and
`GraphQLTestClient.subscribe()` — see [`demo.py`](demo.py) and
[`tests/test_examples_showcase.py`](../../tests/test_examples_showcase.py).
