"""Dependency-free ASGI 3 integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)

Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class ASGIRequest:
    """Native ASGI connection data exposed through ``HTTPContext.request``."""

    scope: dict[str, Any]
    receive: Receive
    send: Send


class GraphQLASGI:
    """ASGI application backed by the shared GraphQL HTTP handler."""

    def __init__(self, schema: Any, **options: Any) -> None:
        self.handler = GraphQLHTTPHandler(schema, **options)
        self.websocket_handler = GraphQLTransportWSHandler(self.handler)

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        scope_type = scope.get("type")
        if scope_type == "websocket":
            await self._websocket(scope, receive, send)
            return
        if scope_type != "http":
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        query_params = dict(
            parse_qsl(
                scope.get("query_string", b"").decode("latin-1"),
                keep_blank_values=True,
            )
        )
        path = _scope_path(scope)
        native = ASGIRequest(scope, receive, send)
        request = HTTPRequest(
            method=scope.get("method", "GET"),
            path=path,
            headers=headers,
            query_params=query_params,
            body=bytes(body),
            native_request=native,
            app=scope.get("app"),
            state=scope.setdefault("state", {}),
        )
        response = await self.handler.handle(request)
        response_headers = [
            (key.encode("latin-1"), value.encode("latin-1"))
            for key, value in response.headers.items()
        ]
        await send(
            {
                "type": "http.response.start",
                "status": response.status,
                "headers": response_headers,
            }
        )
        if not response.is_streaming:
            await send({"type": "http.response.body", "body": response.body})
            return
        stream = response.body
        try:
            async for chunk in stream:
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    }
                )
            await send(
                {"type": "http.response.body", "body": b"", "more_body": False}
            )
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()

    async def _websocket(
        self, scope: dict[str, Any], receive: Receive, send: Send
    ) -> None:
        if "path" not in scope:
            await send({"type": "websocket.close", "code": 1003})
            return
        if _scope_path(scope) != self.handler.endpoints.path:
            await send({"type": "websocket.close", "code": 4404})
            return
        offered = scope.get("subprotocols", [])
        if GRAPHQL_TRANSPORT_WS_PROTOCOL not in offered:
            await send({"type": "websocket.close", "code": 4406})
            return
        message = await receive()
        if message.get("type") != "websocket.connect":
            await send({"type": "websocket.close", "code": 4400})
            return
        await send(
            {
                "type": "websocket.accept",
                "subprotocol": GRAPHQL_TRANSPORT_WS_PROTOCOL,
            }
        )
        disconnected = False

        async def receive_message():
            nonlocal disconnected
            incoming = await receive()
            if incoming.get("type") == "websocket.disconnect":
                disconnected = True
                return None
            raw = incoming.get("text")
            if raw is None and incoming.get("bytes") is not None:
                raw = incoming["bytes"].decode("utf-8")
            try:
                value = json.loads(raw or "")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {"type": "__invalid__"}
            return value if isinstance(value, dict) else {"type": "__invalid__"}

        async def send_message(message: dict[str, Any]) -> None:
            await send(
                {
                    "type": "websocket.send",
                    "text": json.dumps(message, separators=(",", ":")),
                }
            )

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        native = ASGIRequest(scope, receive, send)
        request = HTTPRequest(
            method="GET",
            path=_scope_path(scope),
            headers=headers,
            native_request=native,
            app=scope.get("app"),
            state=scope.setdefault("state", {}),
        )
        await self.websocket_handler.handle(
            receive_message,
            send_message,
            request=request,
        )
        if not disconnected:
            await send({"type": "websocket.close", "code": 1000})


def _scope_path(scope: dict[str, Any]) -> str:
    path = scope.get("path", "/")
    root_path = scope.get("root_path", "")
    if root_path and path.startswith(root_path):
        return path[len(root_path):] or "/"
    return path


__all__ = ["ASGIRequest", "GraphQLASGI"]
