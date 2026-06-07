"""Tests for the dependency-free ASGI adapter."""

from __future__ import annotations

import json

from fastql.integrations import ASGIRequest, GraphQLASGI
from fastql.registry import TypeRegistry
from fastql.schema_builder import build_schema
from fastql.types import Field, NonNull, ObjectType, String


def make_schema():
    query = ObjectType(
        "Query",
        fields={
            "ping": Field(NonNull(String), resolver=lambda: "pong"),
            "scopeType": Field(
                NonNull(String), resolver=lambda ctx: ctx.request.scope["type"]
            ),
        },
    )
    return build_schema(query=query, registry=TypeRegistry())


async def invoke(
    app, *, method="POST", path="/graphql", root_path="", payload=None, headers=None
):
    sent = []
    body = json.dumps(payload).encode() if payload is not None else b""
    request_messages = [
        {"type": "http.request", "body": body, "more_body": False}
    ]

    async def receive():
        return request_messages.pop(0)

    async def send(message):
        sent.append(message)

    raw_headers = [(b"content-type", b"application/json")] if payload is not None else []
    raw_headers.extend(headers or [])
    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": method,
            "path": path,
            "root_path": root_path,
            "query_string": b"",
            "headers": raw_headers,
            "state": {},
        },
        receive,
        send,
    )
    return sent


async def test_asgi_executes_and_exposes_native_connection():
    app = GraphQLASGI(make_schema())
    sent = await invoke(
        app, payload={"query": "{ ping scopeType }"}
    )
    assert sent[0]["status"] == 200
    assert json.loads(sent[1]["body"])["data"] == {
        "ping": "pong",
        "scopeType": "http",
    }

    mounted = await invoke(
        app,
        path="/api/graphql",
        root_path="/api",
        payload={"query": "{ ping }"},
    )
    assert json.loads(mounted[1]["body"])["data"] == {"ping": "pong"}


async def test_asgi_companion_endpoints_and_response_headers():
    async def context_factory(context):
        assert isinstance(context.request, ASGIRequest)
        context.response.set_header("x-adapter", "asgi")

    app = GraphQLASGI(
        make_schema(),
        context_factory=context_factory,
        graphiql=True,
        schema_path="/schema.graphql",
    )
    sent = await invoke(app, payload={"query": "{ ping }"})
    assert (b"x-adapter", b"asgi") in sent[0]["headers"]
    schema = await invoke(app, method="GET", path="/schema.graphql")
    assert b"type Query" in schema[1]["body"]


async def test_asgi_malformed_request_and_disconnect():
    app = GraphQLASGI(make_schema())
    malformed = await invoke(app, payload=None)
    assert malformed[0]["status"] == 415

    sent = []

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await app({"type": "http", "method": "POST", "path": "/graphql"}, receive, send)
    assert sent == []


async def test_asgi_closes_unsupported_websocket_scope():
    app = GraphQLASGI(make_schema())
    sent = []

    async def receive():
        return {"type": "websocket.connect"}

    async def send(message):
        sent.append(message)

    await app({"type": "websocket"}, receive, send)
    assert sent == [{"type": "websocket.close", "code": 1003}]
