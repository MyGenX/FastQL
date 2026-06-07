# FastQL

A code-first, decorator-driven GraphQL framework for Python with a **hand-built engine**
(lexer → parser → validator → executor), a built-in **dependency-injection / context** layer,
and a **web-framework-agnostic core** — zero runtime dependencies, Python 3.11+.

> Status: early development. The core engine (parse → build → validate → execute, with
> dependency injection and introspection) is in place.

**Documentation:** Start with the [FastQL documentation](docs/index.mdx), then use the
[capability catalog](docs/specifications/capability-catalog.mdx) to trace documented
behavior to its canonical OpenSpec requirements.

## Quickstart

Define types and operations with decorators — field and argument types come from your
Python type hints. Resolvers are plain functions; the executor injects arguments, the
parent object, resolve `info`, and the `Context` based on each resolver's signature.

```python
import asyncio
from typing import Annotated
from fastql import Argument, Context, Field, Query, Schema, Type, execute


@Type
class User:                  # just fields — constructor/repr/eq are auto-generated
    id: int
    full_name: str

    @Field
    def loud_name(self) -> str:   # exposed as loudName by default
        return self.full_name.upper()


class AppContext(Context):
    def __init__(self, users):
        self.users = users


@Query                       # group related queries on a class…
class Queries:
    @Field
    async def user(
        self,
        user_id: Annotated[int, Argument(name="id")],
        ctx: Context,
    ) -> "User | None":
        return ctx.users.get(user_id)

    @Field
    def ping(self) -> str:    # sync resolvers work alongside async ones
        return "pong"


schema = Schema(query=Queries)


async def main():
    ctx = AppContext(users={1: User(1, "Ada Lovelace")})
    result = await execute(schema, "{ user(id: 1) { id fullName loudName } ping }", context=ctx)
    print(result.data)       # {'user': {'id': 1, 'fullName': 'Ada Lovelace', 'loudName': 'ADA LOVELACE'}, 'ping': 'pong'}


asyncio.run(main())
```

`@Type` and `@Input` classes get generated constructors, `repr`, and equality unless they define
their own methods. Python snake_case fields and arguments become GraphQL camelCase by default;
pass `SchemaConfig(auto_camel_case=False)` to `Schema` to preserve Python names. Explicit `name=`
metadata always wins. `build_schema()` remains available for applications that intentionally merge
multiple globally decorated root classes.

`execute` returns an `ExecutionResult` with `data`, `errors`, and `extensions`, and a
`.formatted()` helper that produces the GraphQL-over-HTTP response shape. Introspection
(`__schema`, `__type`, `__typename`) is built in.

A runnable version of this lives in [`examples/hello.py`](examples/hello.py).

The documentation quickstart and first-schema examples are also executed by the test
suite from [`docs/snippets`](docs/snippets).

## Dev server & playground

Try a schema in the browser with the built-in, zero-dependency dev server:

```bash
python -m fastql serve examples.hello:schema      # http://127.0.0.1:7691
```

It serves, on the default port **7691**:

| Route             | Description                                  |
| ----------------- | -------------------------------------------- |
| `GET /`           | GraphiQL IDE (loaded from CDN)               |
| `POST/GET /graphql` | the GraphQL endpoint (`{data, errors}` JSON) |
| `GET /schema.graphql` | the schema as SDL                        |
| `GET /schema.json`    | the schema as an introspection result    |

Override the binding with `--host` / `--port`. If your resolvers need a `Context`,
point `--context` at a value or zero-arg factory:

```bash
python -m fastql serve examples.hello:schema --context examples.hello:make_context
```

Or call it programmatically:

```python
import fastql
from examples.hello import schema, make_context

fastql.serve(schema, port=7691, context_factory=make_context)  # blocking; Ctrl-C to stop
```

The dev server lives outside the agnostic core (in `fastql.server`) and only
consumes `build_schema` / `execute` — it is a developer convenience, not a
production transport (no TLS, auth, or subscriptions).

## Design at a glance

```
@Type / @Input / root class decorators  ← unified type-hint-driven authoring
        ▼
Schema(query=...) / build_schema()       ← compiles decorators into the type-system IR
        ▼
Type-system IR (Schema, ObjectType, Field, scalars, wrappers)
        ▼
execute() ── validation ── coercion ── async resolution + DI/context
        ▲
language: Source → Lexer → Parser → AST  ← hand-built front-end
```

The core never imports an HTTP framework. Transports (an optional built-in dev server,
plus FastAPI/Django/Flask/ASGI adapters) plug in on top and consume `build_schema` / `execute`.

## Web framework integrations

Install only the framework adapter an application uses:

```bash
pip install fastql[fastapi]   # or starlette, flask, django
```

```python
from fastapi import FastAPI
from fastql.integrations.fastapi import create_fastapi_router

app = FastAPI()
app.include_router(create_fastapi_router(schema, graphiql=True))
```

The base installation includes the dependency-free `GraphQLASGI` adapter. See
the [integration documentation](docs/integrations/overview.mdx) for mounting,
request context, endpoint configuration, and supported versions.

## Development

```bash
pip install -e ".[dev]"
pytest
```
