"""Dependency-free ASGI 3 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest

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

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        scope_type = scope.get("type")
        if scope_type == "websocket":
            await send({"type": "websocket.close", "code": 1003})
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
        path = scope.get("path", "/")
        root_path = scope.get("root_path", "")
        if root_path and path.startswith(root_path):
            path = path[len(root_path):] or "/"
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
        await send({"type": "http.response.body", "body": response.body})


__all__ = ["ASGIRequest", "GraphQLASGI"]
