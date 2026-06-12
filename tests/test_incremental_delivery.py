"""Incremental delivery: ``@defer`` fragments and ``@stream`` list fields."""

from __future__ import annotations

import json

import pytest

from fastql import Field, Query, Schema, execute, execute_incremental, validate
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.integrations import GraphQLHTTPHandler, HTTPRequest
from fastql.language import parse


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def make_schema():
    from fastql import Type

    @Type
    class User:
        id: int
        name: str
        bio: str

    @Query
    class Q:
        @Field
        def user(self) -> User:
            return User(1, "Ada", "Pioneer of computing")

        @Field
        def numbers(self) -> list[int]:
            return [10, 20, 30, 40]

        @Field
        def total(self) -> int:
            return 4

    return Schema(query=Q)


async def _collect(schema, query, **kwargs):
    return [payload async for payload in execute_incremental(schema, query, **kwargs)]


async def test_deferred_inline_fragment_delivered_later():
    schema = make_schema()
    query = "{ user { id ... on User @defer { name bio } } }"

    payloads = await _collect(schema, query)

    assert payloads[0] == {"data": {"user": {"id": 1}}, "hasNext": True}
    assert payloads[-1]["hasNext"] is False
    incremental = payloads[1]["incremental"][0]
    assert incremental["path"] == ["user"]
    assert incremental["data"] == {"name": "Ada", "bio": "Pioneer of computing"}


async def test_deferred_fragment_spread_delivered_later():
    schema = make_schema()
    query = "query { user { id ...Details @defer } } fragment Details on User { name }"

    payloads = await _collect(schema, query)

    assert payloads[0] == {"data": {"user": {"id": 1}}, "hasNext": True}
    assert payloads[1]["incremental"][0]["data"] == {"name": "Ada"}
    assert payloads[1]["hasNext"] is False


async def test_defer_if_false_inlines_with_no_incremental_payload():
    schema = make_schema()
    query = "{ user { id ... on User @defer(if: false) { name } } }"

    payloads = await _collect(schema, query)

    assert payloads == [
        {"data": {"user": {"id": 1, "name": "Ada"}}, "hasNext": False}
    ]


async def test_streamed_list_returns_initial_then_remaining_items():
    schema = make_schema()
    query = "{ numbers @stream(initialCount: 1) }"

    payloads = await _collect(schema, query)

    assert payloads[0] == {"data": {"numbers": [10]}, "hasNext": True}
    # Remaining items arrive one per payload, appended at their list index.
    assert payloads[1]["incremental"][0] == {"items": [20], "path": ["numbers", 1]}
    assert payloads[2]["incremental"][0] == {"items": [30], "path": ["numbers", 2]}
    assert payloads[3]["incremental"][0] == {"items": [40], "path": ["numbers", 3]}
    assert payloads[3]["hasNext"] is False


async def test_non_streaming_transport_collapses_to_single_result():
    schema = make_schema()
    query = (
        "{ user { id ... on User @defer { name bio } } "
        "numbers @stream(initialCount: 1) }"
    )

    # execute() ignores @defer/@stream and resolves everything inline.
    result = await execute(schema, query)

    assert result.errors == []
    assert result.data == {
        "user": {"id": 1, "name": "Ada", "bio": "Pioneer of computing"},
        "numbers": [10, 20, 30, 40],
    }


def test_stream_on_non_list_field_is_invalid():
    schema = make_schema()
    document = parse("{ total @stream }")

    errors = validate(schema, document)

    assert any("@stream" in error.message for error in errors)


def test_defer_and_stream_are_known_directives():
    schema = make_schema()
    assert {"defer", "stream"} <= set(schema.directives)
    # A defer/stream document is otherwise valid.
    assert validate(schema, parse("{ numbers @stream(initialCount: 1) }")) == []


async def test_multipart_transport_streams_incremental_payloads():
    payload = json.dumps(
        {"query": "{ user { id ... on User @defer { name } } }"}
    ).encode()
    request = HTTPRequest(
        "POST",
        "/graphql",
        headers={
            "content-type": "application/json",
            "accept": "multipart/mixed",
        },
        body=payload,
    )

    response = await GraphQLHTTPHandler(make_schema()).handle(request)
    body = b"".join([chunk async for chunk in response.body])

    assert response.status == 200
    assert response.headers["content-type"] == 'multipart/mixed; boundary="graphql"'
    # Initial payload plus one incremental payload, then the closing boundary.
    assert body.count(b"content-type: application/json") == 2
    assert b'"hasNext":true' in body
    assert b'"incremental"' in body
    assert b'{"name":"Ada"}' in body
    assert body.rstrip().endswith(b"--graphql--")


async def test_plain_query_over_streaming_accept_returns_single_json():
    # No @defer/@stream -> the handler must not switch to incremental streaming.
    payload = json.dumps({"query": "{ user { id name } }"}).encode()
    request = HTTPRequest(
        "POST",
        "/graphql",
        headers={
            "content-type": "application/json",
            "accept": "multipart/mixed",
        },
        body=payload,
    )

    response = await GraphQLHTTPHandler(make_schema()).handle(request)

    # A non-incremental query yields a single buffered JSON body, not a stream.
    assert isinstance(response.body, bytes)
    assert "multipart/mixed" not in response.headers["content-type"]
    assert json.loads(response.body) == {"data": {"user": {"id": 1, "name": "Ada"}}}
