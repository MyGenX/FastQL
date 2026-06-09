"""Relay global object identification and cursor pagination.

This schema is intentionally separate from ``examples.app`` because that showcase
already has a domain-specific ``Node`` interface whose ID is an integer.
"""

from fastql import Field, ID, Info, Schema, Type, TypeRegistry
from fastql.relay import (
    Connection,
    Edge,
    Node,
    PageInfo,
    connection_from_list,
    register_node,
    resolve_node,
    to_global_id,
)


@Type(interfaces=[Node])
class RelayUser:
    database_id: int = Field(private=True)
    name: str

    @Field
    def id(self) -> ID:
        return to_global_id("RelayUser", self.database_id)


USERS = [
    RelayUser(1, "Ada"),
    RelayUser(2, "Grace"),
    RelayUser(3, "Linus"),
    RelayUser(4, "Margaret"),
]


def _fetch_user(inner_id: str, info: Info | None = None) -> RelayUser | None:
    del info
    try:
        database_id = int(inner_id)
    except ValueError:
        return None
    return next((user for user in USERS if user.database_id == database_id), None)


def register_nodes() -> None:
    """Register cookbook node resolvers; safe to call repeatedly."""
    register_node("RelayUser", _fetch_user)


register_nodes()


@Type(name="Query")
class Queries:
    @Field
    def node(self, id: ID, info: Info) -> Node | None:
        return resolve_node(id, info)

    @Field
    def users(
        self,
        first: int | None = None,
        after: str | None = None,
        last: int | None = None,
        before: str | None = None,
    ) -> Connection[RelayUser]:
        return connection_from_list(
            USERS, first=first, after=after, last=last, before=before
        )


registry = TypeRegistry()
for type_ in (Node, PageInfo, RelayUser, Queries):
    registry.register_type(type_, type_.__fastql_type__)
for template in (Edge, Connection):
    registry.generic_templates[template] = template.__fastql_generic__

schema = Schema(query=Queries, registry=registry)

__all__ = ["Queries", "RelayUser", "USERS", "register_nodes", "schema"]
