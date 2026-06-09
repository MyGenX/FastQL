"""Relay pagination: Node resolution, global IDs, connections, cursor slicing."""

import pytest

from fastql import Field, Info, Query, Schema, Type, execute
from fastql import relay
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.relay import (
    Connection,
    Node,
    connection_from_list,
    from_global_id,
    offset_to_cursor,
    register_node,
    resolve_node,
    to_global_id,
)
from fastql.types import ID

DATA = {index: f"User{index}" for index in range(1, 6)}


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()
    relay.clear_node_registry()
    relay.register_types()  # restore Relay types after the clear


def _build_schema():
    @Type(interfaces=[Node])
    class User:
        inner_id: int
        name: str

        @Field
        def id(self) -> ID:
            return to_global_id("User", self.inner_id)

    def fetch_user(inner_id, info=None):
        uid = int(inner_id)
        return User(inner_id=uid, name=DATA[uid]) if uid in DATA else None

    register_node("User", fetch_user)
    all_users = [User(inner_id=i, name=DATA[i]) for i in sorted(DATA)]

    @Query
    class Q:
        @Field
        def node(self, id: ID, info: Info) -> "Node | None":
            return resolve_node(id, info)

        @Field
        def users(
            self,
            first: int | None = None,
            after: str | None = None,
            last: int | None = None,
            before: str | None = None,
        ) -> Connection[User]:
            return connection_from_list(
                all_users, first=first, after=after, last=last, before=before
            )

    return Schema(query=Q)


def test_global_id_round_trips():
    encoded = to_global_id("User", 42)
    assert from_global_id(encoded) == ("User", "42")
    assert from_global_id("not-a-valid-id") == ("", "")


async def test_node_resolves_object_by_global_id_with_typename():
    schema = _build_schema()
    gid = to_global_id("User", 3)

    result = await execute(
        schema, '{ node(id: "%s") { __typename ... on User { name } } }' % gid
    )

    assert result.errors == []
    assert result.data == {"node": {"__typename": "User", "name": "User3"}}


def test_connection_exposes_relay_shape():
    schema = _build_schema()

    assert "UserConnection" in schema.type_map
    assert "UserEdge" in schema.type_map
    assert "PageInfo" in schema.type_map
    edge = schema.type_map["UserEdge"]
    assert set(edge.fields) == {"node", "cursor"}
    page_info = schema.type_map["PageInfo"]
    assert {
        "hasNextPage",
        "hasPreviousPage",
        "startCursor",
        "endCursor",
    } <= set(page_info.fields)


async def test_forward_pagination_first_after():
    schema = _build_schema()
    after = offset_to_cursor(1)  # skip the first two (offsets 0,1)

    result = await execute(
        schema,
        '{ users(first: 2, after: "%s") {'
        " edges { node { name } cursor } pageInfo { hasNextPage hasPreviousPage }"
        " } }" % after,
    )

    users = result.data["users"]
    assert [edge["node"]["name"] for edge in users["edges"]] == ["User3", "User4"]
    assert users["pageInfo"] == {"hasNextPage": True, "hasPreviousPage": False}


async def test_backward_pagination_last_before():
    schema = _build_schema()
    before = offset_to_cursor(4)  # before the last element (offset 4)

    result = await execute(
        schema,
        '{ users(last: 2, before: "%s") {'
        " edges { node { name } } pageInfo { hasNextPage hasPreviousPage }"
        " } }" % before,
    )

    users = result.data["users"]
    assert [edge["node"]["name"] for edge in users["edges"]] == ["User3", "User4"]
    assert users["pageInfo"]["hasPreviousPage"] is True


async def test_first_returns_capped_page_with_has_next_page():
    schema = _build_schema()

    result = await execute(
        schema, "{ users(first: 2) { edges { node { name } } pageInfo { hasNextPage } } }"
    )

    users = result.data["users"]
    assert [edge["node"]["name"] for edge in users["edges"]] == ["User1", "User2"]
    assert users["pageInfo"]["hasNextPage"] is True
