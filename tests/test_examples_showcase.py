"""Coverage of the ``examples.app`` showcase via ``GraphQLTestClient``.

Exercises each GraphQL concept the showcase demonstrates: custom scalar, enum, interface,
union, input + mutation, permissions, field/schema extensions, dependency injection,
DataLoader batching, and subscriptions over the core ``subscribe()`` path.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from fastql import GraphQLTestClient

from examples.app import STORE, AppContext, reseed, schema
from examples.app.loaders import BATCH_CALLS
from examples.app.mutations import AuditLog
from examples.app.providers import register_dependencies
from examples.app.pubsub import pubsub


@pytest.fixture(autouse=True)
def fresh_state():
    # Other test modules clear the global registries; restore what the showcase needs.
    reseed()
    register_dependencies()
    BATCH_CALLS.clear()
    AuditLog.entries.clear()
    yield


def client(*, user_id: int | None = 1) -> GraphQLTestClient:
    current = STORE.users.get(user_id) if user_id is not None else None
    return GraphQLTestClient(schema, context=AppContext(current_user=current))


async def test_custom_scalar_serializes_datetime():
    result = await client().execute("{ node(id: 10) { ... on Post { createdAt } } }")
    value = result.data["node"]["createdAt"]
    # Round-trips as ISO-8601 (the DateTime scalar's serialize output).
    assert datetime.fromisoformat(value).year == 2024


async def test_enum_field_serializes_to_member_name():
    result = await client().execute("{ user(id: 1) { role } }")
    assert result.data == {"user": {"role": "ADMIN"}}


async def test_interface_node_resolves_concrete_type():
    result = await client().execute(
        '{ node(id: 10) { __typename ... on Post { title } } }'
    )
    assert result.data == {"node": {"__typename": "Post", "title": "On the Analytical Engine"}}


async def test_union_search_returns_mixed_members():
    result = await client().execute(
        '{ search(term: "first") { __typename ... on Post { title } ... on User { name } } }'
    )
    assert {"__typename": "Post", "title": "The First Compiler"} in result.data["search"]


async def test_input_and_mutation_create_post():
    result = await client().execute(
        'mutation { createPost(input: { title: "New", body: "b", status: PUBLISHED })'
        " { title status author { name } } }"
    )
    assert result.errors == []
    assert result.data["createPost"] == {
        "title": "New",
        "status": "PUBLISHED",
        "author": {"name": "Ada Lovelace"},
    }


async def test_posts_filter_by_enum_input():
    result = await client().execute("{ posts(filter: { status: PUBLISHED }) { title } }")
    titles = {p["title"] for p in result.data["posts"]}
    assert titles == {"On the Analytical Engine", "The First Compiler"}  # excludes the DRAFT


async def test_permission_denied_for_anonymous_mutation():
    result = await client(user_id=None).execute(
        'mutation { createPost(input: { title: "x", body: "y" }) { id } }'
    )
    # createPost is non-null, so a denied permission null-bubbles to a null root.
    assert result.data is None
    assert any("Authentication required" in e.message for e in result.errors)


async def test_admin_only_mutation_requires_admin():
    member = await client(user_id=2).execute("mutation { publishPost(id: 11) { status } }")
    assert any("Admin role required" in e.message for e in member.errors)

    admin = await client(user_id=1).execute("mutation { publishPost(id: 11) { status } }")
    assert admin.data == {"publishPost": {"status": "PUBLISHED"}}


async def test_field_extension_audits_mutation():
    await client().execute('mutation { createPost(input: { title: "Audited", body: "b" }) { id } }')
    assert any(name == "create_post" for name, _ in AuditLog.entries)


async def test_dependency_injection_provides_clock():
    result = await client().execute("{ serverTime }")
    assert result.errors == []
    assert datetime.fromisoformat(result.data["serverTime"])  # parseable timestamp


async def test_dataloader_batches_relationship_loads():
    result = await client().execute("{ users { name posts { title } } }")
    assert result.errors == []
    # One batched load for both users, not one per user.
    assert BATCH_CALLS == [[1, 2]]


async def test_schema_extensions_report_metadata():
    result = await client().execute("{ ping }")
    assert "timing" in result.extensions
    assert result.extensions["resolverCount"] >= 1


async def test_subscription_post_added_fed_by_mutation():
    c = client()
    received: list = []
    stream = c.subscribe("subscription { postAdded { title author { name } } }")

    async def consume() -> None:
        async for event in stream:
            received.append(event.data)
            break

    consumer = asyncio.create_task(consume())
    while not pubsub.has_subscribers("post_added"):
        await asyncio.sleep(0)

    await c.execute('mutation { createPost(input: { title: "Streamed", body: "b" }) { id } }')
    await consumer
    await stream.aclose()

    assert received == [{"postAdded": {"title": "Streamed", "author": {"name": "Ada Lovelace"}}}]
