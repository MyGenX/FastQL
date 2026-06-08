"""Root queries.

Each ``@Field`` method on the ``@Query`` class is a root query. Resolver parameters are
bound by role: GraphQL arguments by name, the ``Context`` and ``Info`` by type, and
registered services (``Clock``) by type via dependency injection. Reads go through the
module-level ``STORE`` so the queries also work without a request context (e.g. through
the dev server).
"""

from __future__ import annotations

from fastql import Context, Field, Query

from examples.app.context import AppContext
from examples.app.data import STORE
from examples.app.enums import as_status
from examples.app.interfaces import Node
from examples.app.inputs import PostFilter
from examples.app.providers import Clock
from examples.app.scalars import DateTime
from examples.app.types import Post, SearchResult, User


@Query
class Queries:
    @Field
    def ping(self) -> str:
        return "pong"

    @Field
    def node(self, id: int) -> "Node | None":
        # Returns any type implementing Node; the executor picks the concrete one.
        return STORE.find_node(id)

    @Field
    def user(self, id: int) -> "User | None":
        return STORE.users.get(id)

    @Field
    def users(self) -> list[User]:
        return list(STORE.users.values())

    @Field
    def posts(self, filter: "PostFilter | None" = None) -> list[Post]:
        results = list(STORE.posts.values())
        if filter is not None:
            if filter.status is not None:
                want = as_status(filter.status)
                results = [p for p in results if as_status(p.status) == want]
            if filter.published_since is not None:
                results = [p for p in results if p.created_at >= filter.published_since]
        return results

    @Field
    def search(self, term: str) -> list[SearchResult]:
        needle = term.lower()
        hits: list = [u for u in STORE.users.values() if needle in u.name.lower()]
        hits += [p for p in STORE.posts.values() if needle in p.title.lower()]
        return hits

    @Field
    def me(self, ctx: Context) -> "User | None":
        return ctx.current_user if isinstance(ctx, AppContext) else None

    @Field
    def server_time(self, clock: Clock) -> DateTime:
        # ``clock`` is injected by the DI registry, not a GraphQL argument.
        return clock.now()


__all__ = ["Queries"]
