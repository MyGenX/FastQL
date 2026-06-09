# FastQL examples

This directory contains runnable examples for the core authoring API, advanced schema
features, and supported web-framework integrations.

| Directory | Purpose |
| --- | --- |
| [`app/`](app) | Main blog/community showcase covering types, operations, execution, and application structure |
| [`advanced/`](advanced) | Small isolated recipes for generics, Relay, directives, visibility, and enum metadata |
| [`projects/`](projects) | Raw ASGI, FastAPI, Starlette, Flask, and Django apps mounting the same showcase schema |

## Installation

The examples are source-tree resources and are not bundled in the published Python
wheel. Clone the repository and run commands from its root:

```bash
git clone https://github.com/MyGenX/FastQL.git
cd FastQL
```

Using `uv` is recommended for repository development:

```bash
# Install FastQL and every optional framework used by the examples.
uv sync --all-extras
```

An editable `pip` installation works as well:

```bash
# Core showcase and advanced cookbook.
python -m pip install -e .

# All framework integrations.
python -m pip install -e ".[all]" uvicorn

# Or install one integration only.
python -m pip install -e ".[fastapi]" uvicorn
```

FastQL requires Python 3.11 or newer.

## Run the showcase

The main showcase is framework-agnostic. It can run directly, through FastQL's
development server, or through any project under [`projects/`](projects).

```bash
# Execute queries, a mutation, DataLoader batching, and a subscription in the terminal.
uv run python -m examples.app.demo

# Open GraphiQL at http://127.0.0.1:7691.
uv run python -m fastql serve examples.app:schema \
    --context examples.app:make_context

# Print the generated GraphQL SDL.
uv run python -m fastql export-schema examples.app:schema
```

Without `uv`, remove the `uv run` prefix after installing the project into the active
environment.

The development server exposes:

| Route | Description |
| --- | --- |
| `GET /` | GraphiQL IDE |
| `POST /graphql` | GraphQL endpoint |
| `GET /schema.graphql` | Generated SDL |
| `GET /schema.json` | Introspection result |

The default context signs requests in as Ada Lovelace, the seeded administrator. The
framework projects instead read an `X-User-Id` header: use `1` for Ada, `2` for Grace,
or omit it for an anonymous request.

## Showcase application structure

[`examples.app`](app) is a small in-memory blog/community API organized like an
application rather than a single tutorial script:

```text
examples/app/
├── schema.py          # assembles the query, mutation, and subscription roots
├── types.py           # User, Post, Comment, union, relationships, computed fields
├── interfaces.py      # application-specific Node interface with integer IDs
├── enums.py           # roles/statuses and enum value metadata
├── scalars.py         # DateTime serialization and input parsing
├── inputs.py          # mutation and filtering input objects
├── queries.py         # read operations and dependency-injected resolvers
├── mutations.py       # authenticated writes and a field extension
├── subscriptions.py   # async post/comment event streams
├── data.py            # seeded in-memory store and relationship indexes
├── loaders.py         # request-scoped DataLoader batch functions
├── context.py         # current-user request context
├── permissions.py     # authentication and admin authorization
├── providers.py       # dependency registration
├── extensions.py      # operation timing and resolver-count extensions
├── pubsub.py           # in-process subscription fan-out
└── demo.py             # standalone executable tour
```

The dependency direction is deliberate:

```text
schema roots -> application services/loaders -> in-memory store
       |                    |
       +-> context, permissions, extensions, and pub/sub
```

All framework projects import the same `examples.app:schema`. They only translate an
HTTP request into FastQL context and mount the shared GraphQL handler, demonstrating
that schema and resolver code is independent of the selected web framework.

See [`app/README.md`](app/README.md) for the complete feature-to-file map.

## Advanced cookbook

Run the Phase 2 recipes together:

```bash
uv run python -m examples.advanced.demo
```

The cookbook keeps each schema independent:

- [`generics.py`](advanced/generics.py) synthesizes `UserPage` and `PostPage` from
  one `Page[T]` template.
- [`relay.py`](advanced/relay.py) demonstrates global IDs, Relay `Node`, and cursor
  connections without conflicting with the showcase's integer-ID `Node`.
- [`schema_metadata.py`](advanced/schema_metadata.py) demonstrates custom directives,
  private/external fields, and customized enum members.

See [`advanced/README.md`](advanced/README.md) for more detail.

## Framework projects

After installing the relevant extras, launch one project from the repository root:

| Integration | Command | Default URL |
| --- | --- | --- |
| Raw ASGI | `uv run --with uvicorn uvicorn examples.projects.asgi.app:application` | `http://127.0.0.1:8000/graphql` |
| FastAPI | `uv run --with uvicorn uvicorn examples.projects.fastapi.app:app` | `http://127.0.0.1:8000/graphql` |
| Starlette | `uv run --with uvicorn uvicorn examples.projects.starlette.app:app` | `http://127.0.0.1:8000/graphql` |
| Flask | `uv run flask --app examples.projects.flask.app run` | `http://127.0.0.1:5000/graphql` |
| Django | `DJANGO_SETTINGS_MODULE=examples.projects.django.settings uv run --with uvicorn uvicorn examples.projects.django.asgi:application` | `http://127.0.0.1:8000/graphql` |

Example request:

```bash
curl -s http://127.0.0.1:8000/graphql \
    -H 'content-type: application/json' \
    -H 'X-User-Id: 1' \
    -d '{"query":"{ me { name role } users { name posts { title } } }"}'
```

Each project has its own README with adapter-specific details. Subscription execution is
shown by `examples.app.demo`; WebSocket/SSE subscription transport is not implemented yet.

## Tests

The examples are exercised as part of the repository test suite:

```bash
uv run pytest tests/test_examples_showcase.py tests/test_examples_advanced.py
```
