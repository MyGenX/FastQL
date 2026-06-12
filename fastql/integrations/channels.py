"""Django Channels FastQL integration (``graphql-transport-ws`` over WebSocket).

Channels is push-driven (``receive`` is called per frame) while the shared
subscription handler pulls messages, so the consumer bridges the two with a
queue and runs the handler as a background task for the connection's lifetime.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.urls import re_path
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError(
        "The Django Channels adapter requires 'mygenx-fastql[channels]'."
    ) from error

from fastql.integrations.asgi import GraphQLASGI
from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)

_CLOSE_SENTINEL = object()


class GraphQLWebSocketConsumer(AsyncWebsocketConsumer):
    """Channels consumer driving FastQL's ``graphql-transport-ws`` handler."""

    schema: Any = None
    handler_options: dict[str, Any] | None = None

    async def connect(self) -> None:
        if GRAPHQL_TRANSPORT_WS_PROTOCOL not in self.scope.get("subprotocols", []):
            await self.close(code=4406)
            return
        await self.accept(subprotocol=GRAPHQL_TRANSPORT_WS_PROTOCOL)
        self._incoming: asyncio.Queue = asyncio.Queue()
        http_handler = GraphQLHTTPHandler(self.schema, **(self.handler_options or {}))
        ws_handler = GraphQLTransportWSHandler(http_handler)
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in self.scope.get("headers", [])
        }
        request = HTTPRequest(
            method="GET",
            path=http_handler.endpoints.path,
            headers=headers,
            native_request=self.scope,
            app=self.scope.get("app"),
            state=self.scope,
        )
        self._task = asyncio.ensure_future(
            ws_handler.handle(self._receive_message, self._send_message, request=request)
        )

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        raw = text_data
        if raw is None and bytes_data is not None:
            raw = bytes_data.decode("utf-8")
        try:
            value = json.loads(raw or "")
        except (json.JSONDecodeError, TypeError):
            value = {"type": "__invalid__"}
        await self._incoming.put(value if isinstance(value, dict) else {"type": "__invalid__"})

    async def disconnect(self, code: int) -> None:
        await self._incoming.put(_CLOSE_SENTINEL)
        task = getattr(self, "_task", None)
        if task is not None:
            await task

    async def _receive_message(self):
        message = await self._incoming.get()
        return None if message is _CLOSE_SENTINEL else message

    async def _send_message(self, payload: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(payload, separators=(",", ":")))


def create_graphql_consumer(schema: Any, **handler_options: Any):
    """Return a configured :class:`GraphQLWebSocketConsumer` subclass."""

    return type(
        "ConfiguredGraphQLWebSocketConsumer",
        (GraphQLWebSocketConsumer,),
        {"schema": schema, "handler_options": handler_options or None},
    )


def create_channels_application(
    schema: Any,
    *,
    path: str = "/graphql",
    http_app: Any = None,
    **options: Any,
) -> "ProtocolTypeRouter":
    """Create a Channels ``ProtocolTypeRouter`` for FastQL HTTP + subscriptions.

    ``http_app`` is the ASGI app handling plain HTTP (typically Django's
    ``get_asgi_application()``); when omitted the shared :class:`GraphQLASGI` app
    serves HTTP too.
    """

    consumer = create_graphql_consumer(schema, path=path, **options)
    return ProtocolTypeRouter(
        {
            "http": http_app or GraphQLASGI(schema, path=path, **options),
            "websocket": URLRouter(
                [re_path(rf"^{path.lstrip('/')}$", consumer.as_asgi())]
            ),
        }
    )


__all__ = [
    "GraphQLWebSocketConsumer",
    "create_channels_application",
    "create_graphql_consumer",
]
