"""A minimal end-to-end FastQL schema.

It demonstrates the core authoring surface plus two production features:

* a **schema extension** (``Timing``) that wraps every operation and reports its
  duration under ``extensions.timing``;
* a **DataLoader** that batches ``User.posts`` lookups so a query over many users
  triggers a single batched load instead of one call per user (no N+1).

Run it through the engine directly::

    import asyncio
    from fastql import execute
    from examples.hello import schema, make_context

    print(asyncio.run(
        execute(schema, '{ user(id: 1) { id name loudName } ping }', context=make_context())
    ).data)

Or serve it in the browser::

    python -m fastql serve examples.hello:schema --context examples.hello:make_context

Or just run this file to see batching + timing in action::

    python -m examples.hello
"""

from __future__ import annotations

import time

from fastql import (
    Context,
    Field,
    Info,
    Query,
    Schema,
    SchemaExtension,
    Type,
    get_loader,
)


class Timing(SchemaExtension):
    """Wrap each operation and surface its wall-clock duration."""

    def on_operation(self):
        self._start = time.perf_counter()
        yield  # the operation runs here
        self._elapsed = time.perf_counter() - self._start

    def get_results(self):
        return {"timing": {"duration_ms": round(self._elapsed * 1000, 3)}}


@Type
class Post:
    id: int
    title: str


@Type
class User:
    # Just fields — the constructor (User(1, "Ada"), repr, eq) is auto-generated.
    id: int
    name: str

    @Field
    def loud_name(self) -> str:
        return self.name.upper()

    @Field
    async def posts(self, info: Info) -> list[Post]:
        # Per-request DataLoader: every User.posts resolved in one operation is
        # batched into a single call to ``batch_load_posts`` (see BATCH_CALLS).
        loader = get_loader(info, batch_load_posts)
        return await loader.load(self.id)


# In-memory "tables".
USERS: dict[int, User] = {
    1: User(1, "Ada Lovelace"),
    2: User(2, "Grace Hopper"),
}
POSTS_BY_USER: dict[int, list[Post]] = {
    1: [Post(10, "On the Analytical Engine"), Post(11, "Notes on Note G")],
    2: [Post(20, "The First Compiler")],
}

# Records each batch invocation so the demo can show how many DB round-trips
# happened — one batched call for the whole `users { posts }` selection.
BATCH_CALLS: list[list[int]] = []


async def batch_load_posts(user_ids: list[int]) -> list[list[Post]]:
    """Batch function: given many user ids, return each user's posts in order."""
    BATCH_CALLS.append(list(user_ids))
    return [POSTS_BY_USER.get(uid, []) for uid in user_ids]


class AppContext(Context):
    """Per-request context carrying an in-memory user store."""

    def __init__(self, users: dict[int, User]):
        self.users = users


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
    def users(self, ctx: Context) -> list["User"]:
        store = ctx.users if ctx is not None else USERS
        return list(store.values())

    @Field
    def ping(self) -> str:
        return "pong"


# Explicit roots are the canonical schema assembly API. ``build_schema()`` is
# still available when modular applications want global root discovery.
schema = Schema(query=Queries, extensions=[Timing])


if __name__ == "__main__":
    import asyncio

    from fastql import execute

    async def main() -> None:
        BATCH_CALLS.clear()
        query = "{ users { name posts { title } } ping }"
        result = await execute(schema, query, context=make_context())
        print("data:", result.data)
        print("extensions:", result.extensions)
        # Two users, but their posts were loaded in a single batched call.
        print("batch calls:", BATCH_CALLS)

    asyncio.run(main())
