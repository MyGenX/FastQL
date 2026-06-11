"""Bounded JSON operation batching tests."""

from __future__ import annotations

import json

from fastql.integrations import GraphQLHTTPHandler, HTTPRequest
from fastql.registry import TypeRegistry
from fastql.schema_builder import build_schema
from fastql.types import Argument, Field, Int, NonNull, ObjectType, String


def make_schema():
    query = ObjectType(
        "Query",
        fields={
            "ping": Field(NonNull(String), resolver=lambda: "pong"),
            "echo": Field(
                NonNull(Int),
                args={"value": Argument(NonNull(Int))},
                resolver=lambda value: value,
            ),
        },
    )
    return build_schema(query=query, registry=TypeRegistry())


def batch_request(payload) -> HTTPRequest:
    return HTTPRequest(
        "POST",
        "/graphql",
        headers={"content-type": "application/json"},
        body=json.dumps(payload).encode(),
    )


async def test_batch_returns_positionally_aligned_result_array():
    response = await GraphQLHTTPHandler(
        make_schema(), allow_batching=True
    ).handle(
        batch_request(
            [
                {"query": "{ ping }"},
                {
                    "query": "query($value: Int!) { echo(value: $value) }",
                    "variables": {"value": 7},
                },
            ]
        )
    )

    assert response.status == 200
    assert json.loads(response.body) == [
        {"data": {"ping": "pong"}},
        {"data": {"echo": 7}},
    ]


async def test_batch_isolates_operation_errors():
    response = await GraphQLHTTPHandler(
        make_schema(), allow_batching=True
    ).handle(
        batch_request(
            [
                {"query": "{ missing }"},
                {"query": "{ ping }"},
            ]
        )
    )
    payload = json.loads(response.body)

    assert response.status == 200
    assert "errors" in payload[0]
    assert payload[1] == {"data": {"ping": "pong"}}


async def test_batching_disabled_rejects_array_request():
    response = await GraphQLHTTPHandler(make_schema()).handle(
        batch_request([{"query": "{ ping }"}])
    )

    assert response.status == 400
    assert "disabled" in json.loads(response.body)["errors"][0]["message"]


async def test_oversized_batch_is_rejected_before_execution():
    calls = []
    query = ObjectType(
        "Query",
        fields={
            "ping": Field(
                NonNull(String),
                resolver=lambda: calls.append("called") or "pong",
            )
        },
    )
    schema = build_schema(query=query, registry=TypeRegistry())
    response = await GraphQLHTTPHandler(
        schema,
        allow_batching=True,
        max_batch_size=1,
    ).handle(
        batch_request([{"query": "{ ping }"}, {"query": "{ ping }"}])
    )

    assert response.status == 400
    assert calls == []


async def test_batch_items_must_be_valid_operation_payloads():
    response = await GraphQLHTTPHandler(
        make_schema(), allow_batching=True
    ).handle(batch_request([{"variables": {}}]))

    assert response.status == 400
    assert "Batch item 0" in json.loads(response.body)["errors"][0]["message"]


def test_batch_size_must_be_positive():
    try:
        GraphQLHTTPHandler(make_schema(), max_batch_size=0)
    except ValueError as error:
        assert "positive" in str(error)
    else:  # pragma: no cover
        raise AssertionError("zero max_batch_size was accepted")
