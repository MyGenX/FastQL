"""Transport tests for graphql-transport-ws, SSE, and multipart streams."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

import pytest

from fastql import Field, Query, Schema, Subscription
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.integrations import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLASGI,
    GraphQLHTTPHandler,
    GraphQLTransportWSHandler,
    HTTPRequest,
)


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def make_schema(*, closed: asyncio.Event | None = None):
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def counter(self, to: int = 2) -> AsyncGenerator[int, None]:
            for value in range(to):
                yield value

        @Field
        async def forever(self) -> AsyncGenerator[int, None]:
            try:
                value = 0
                while True:
                    yield value
                    value += 1
                    await asyncio.sleep(3600)
            finally:
                if closed is not None:
                    closed.set()

    return Schema(query=Q, subscription=Sub)


def transport_request() -> HTTPRequest:
    return HTTPRequest("GET", "/graphql")


async def next_message(queue: asyncio.Queue):
    return await asyncio.wait_for(queue.get(), timeout=1)


async def test_websocket_connection_ack_next_and_complete():
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    handler = GraphQLTransportWSHandler(GraphQLHTTPHandler(make_schema()))
    task = asyncio.create_task(
        handler.handle(incoming.get, outgoing.put, request=transport_request())
    )

    await incoming.put({"type": "connection_init"})
    assert await next_message(outgoing) == {"type": "connection_ack"}
    await incoming.put({"type": "ping", "payload": {"probe": True}})
    assert await next_message(outgoing) == {
        "type": "pong",
        "payload": {"probe": True},
    }
    await incoming.put(
        {
            "id": "counter",
            "type": "subscribe",
            "payload": {"query": "subscription { counter(to: 2) }"},
        }
    )

    assert await next_message(outgoing) == {
        "id": "counter",
        "type": "next",
        "payload": {"data": {"counter": 0}},
    }
    assert await next_message(outgoing) == {
        "id": "counter",
        "type": "next",
        "payload": {"data": {"counter": 1}},
    }
    assert await next_message(outgoing) == {"id": "counter", "type": "complete"}

    await incoming.put(None)
    await task


async def test_websocket_invalid_operation_sends_error():
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    handler = GraphQLTransportWSHandler(GraphQLHTTPHandler(make_schema()))
    task = asyncio.create_task(
        handler.handle(incoming.get, outgoing.put, request=transport_request())
    )

    await incoming.put({"type": "connection_init"})
    await next_message(outgoing)
    await incoming.put(
        {
            "id": "bad",
            "type": "subscribe",
            "payload": {"query": "subscription { missing }"},
        }
    )
    message = await next_message(outgoing)
    assert message["id"] == "bad"
    assert message["type"] == "error"
    assert "missing" in message["payload"][0]["message"]

    await incoming.put(None)
    await task


async def test_websocket_client_complete_closes_source_stream():
    closed = asyncio.Event()
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    handler = GraphQLTransportWSHandler(
        GraphQLHTTPHandler(make_schema(closed=closed))
    )
    task = asyncio.create_task(
        handler.handle(incoming.get, outgoing.put, request=transport_request())
    )

    await incoming.put({"type": "connection_init"})
    await next_message(outgoing)
    await incoming.put(
        {
            "id": "forever",
            "type": "subscribe",
            "payload": {"query": "subscription { forever }"},
        }
    )
    assert (await next_message(outgoing))["type"] == "next"
    await incoming.put({"id": "forever", "type": "complete"})
    await asyncio.wait_for(closed.wait(), timeout=1)

    await incoming.put(None)
    await task


async def test_sse_streams_one_data_event_per_result():
    payload = json.dumps(
        {"query": "subscription { counter(to: 2) }"}
    ).encode()
    request = HTTPRequest(
        "POST",
        "/graphql",
        headers={
            "content-type": "application/json",
            "accept": "text/event-stream",
        },
        body=payload,
    )
    response = await GraphQLHTTPHandler(make_schema()).handle(request)
    body = b"".join([chunk async for chunk in response.body])

    assert response.status == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert body.split(b"\n\n")[:-1] == [
        b'data: {"data":{"counter":0}}',
        b'data: {"data":{"counter":1}}',
    ]


async def test_multipart_streams_one_part_per_result():
    payload = json.dumps(
        {"query": "subscription { counter(to: 2) }"}
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
    assert body.count(b"content-type: application/json") == 2
    assert b'{"data":{"counter":0}}' in body
    assert b'{"data":{"counter":1}}' in body
    assert body.endswith(b"--graphql--\r\n")


def test_protocol_name_is_graphql_transport_ws():
    assert GRAPHQL_TRANSPORT_WS_PROTOCOL == "graphql-transport-ws"


async def test_asgi_websocket_adapter_drives_protocol_handler():
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    app = GraphQLASGI(make_schema())
    task = asyncio.create_task(
        app(
            {
                "type": "websocket",
                "path": "/graphql",
                "headers": [],
                "subprotocols": [GRAPHQL_TRANSPORT_WS_PROTOCOL],
                "state": {},
            },
            incoming.get,
            outgoing.put,
        )
    )

    await incoming.put({"type": "websocket.connect"})
    assert await next_message(outgoing) == {
        "type": "websocket.accept",
        "subprotocol": GRAPHQL_TRANSPORT_WS_PROTOCOL,
    }
    await incoming.put(
        {"type": "websocket.receive", "text": '{"type":"connection_init"}'}
    )
    ack = await next_message(outgoing)
    assert json.loads(ack["text"]) == {"type": "connection_ack"}
    await incoming.put(
        {
            "type": "websocket.receive",
            "text": json.dumps(
                {
                    "id": "one",
                    "type": "subscribe",
                    "payload": {"query": "subscription { counter(to: 1) }"},
                }
            ),
        }
    )
    next_event = json.loads((await next_message(outgoing))["text"])
    complete = json.loads((await next_message(outgoing))["text"])
    assert next_event["type"] == "next"
    assert next_event["payload"] == {"data": {"counter": 0}}
    assert complete == {"id": "one", "type": "complete"}

    await incoming.put({"type": "websocket.disconnect", "code": 1000})
    await task


async def test_asgi_adapter_streams_sse_body_chunks():
    sent = []
    request_messages = [
        {
            "type": "http.request",
            "body": json.dumps(
                {"query": "subscription { counter(to: 2) }"}
            ).encode(),
            "more_body": False,
        }
    ]

    async def receive():
        return request_messages.pop(0)

    async def send(message):
        sent.append(message)

    await GraphQLASGI(make_schema())(
        {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [
                (b"content-type", b"application/json"),
                (b"accept", b"text/event-stream"),
            ],
            "state": {},
        },
        receive,
        send,
    )

    assert sent[0]["status"] == 200
    chunks = [message["body"] for message in sent[1:-1]]
    assert chunks == [
        b'data: {"data":{"counter":0}}\n\n',
        b'data: {"data":{"counter":1}}\n\n',
    ]
    assert sent[-1] == {
        "type": "http.response.body",
        "body": b"",
        "more_body": False,
    }
