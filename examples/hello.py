"""A minimal end-to-end FastQL schema.

Run it through the engine directly::

    import asyncio
    from fastql import execute
    from examples.hello import schema, make_context

    print(asyncio.run(
        execute(schema, '{ user(id: 1) { id name loudName } ping }', context=make_context())
    ).data)

Or serve it in the browser::

    python -m fastql serve examples.hello:schema --context examples.hello:make_context
"""

from __future__ import annotations

from fastql import Context, Field, Query, Schema, Type


@Type
class User:
    # Just fields — the constructor (User(1, "Ada"), repr, eq) is auto-generated.
    id: int
    name: str

    @Field
    def loud_name(self) -> str:
        return self.name.upper()


class AppContext(Context):
    """Per-request context carrying an in-memory user store."""

    def __init__(self, users: dict[int, User]):
        self.users = users


# A seeded store, used as the default when no context is supplied.
USERS: dict[int, User] = {
    1: User(1, "Ada Lovelace"),
    2: User(2, "Grace Hopper"),
}


def make_context() -> AppContext:
    """Build a request context. Use with the dev server's --context flag."""
    return AppContext(USERS)


@Query
class Queries:
    """Root queries grouped on a class; each @Field method is a query."""

    @Field
    def user(self, id: int, ctx: Context) -> "User | None":
        store = ctx.users if ctx is not None else USERS
        return store.get(id)

    @Field
    def ping(self) -> str:
        return "pong"


# Explicit roots are the canonical schema assembly API. ``build_schema()`` is
# still available when modular applications want global root discovery.
schema = Schema(query=Queries)
