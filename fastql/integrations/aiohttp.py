"""AIOHTTP-native FastQL application integration."""

from __future__ import annotations

import json
from typing import Any

try:
    from aiohttp import web
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError(
        "The AIOHTTP adapter requires 'mygenx-fastql[aiohttp]'."
    ) from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)


def create_aiohttp_app(
    schema: Any,
    *,
    path: str = "/graphql",
    app: "web.Application | None" = None,
    **options: Any,
) -> "web.Application":
    """Create (or extend) an ``aiohttp`` application exposing FastQL routes."""

    application = app if app is not None else web.Application()
    handler = GraphQLHTTPHandler(schema, path=path, **options)
    websocket_handler = GraphQLTransportWSHandler(handler)

    def make_view(target_path: str):
        async def view(request: "web.Request") -> "web.StreamResponse":
            if (
                target_path == handler.endpoints.path
                and request.headers.get("upgrade", "").lower() == "websocket"
            ):
                return await _websocket(request)
            normalized = HTTPRequest(
                method=request.method,
                path=target_path,
                headers=request.headers,
                query_params=request.query,
                body=await request.read(),
                native_request=request,
                app=request.app,
                state=request,
            )
            result = await handler.handle(normalized)
            if result.is_streaming:
                response = web.StreamResponse(
                    status=result.status, headers=result.headers
                )
                await response.prepare(request)
                async for chunk in result.body:
                    await response.write(chunk)
                await response.write_eof()
                return response
            return web.Response(
                body=result.body, status=result.status, headers=result.headers
            )

        return view

    async def _websocket(request: "web.Request") -> "web.WebSocketResponse":
        websocket = web.WebSocketResponse(protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL])
        await websocket.prepare(request)

        async def receive_message():
            message = await websocket.receive()
            if message.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSING,
                                 web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                return None
            try:
                value = json.loads(message.data)
            except (json.JSONDecodeError, TypeError):
                return {"type": "__invalid__"}
            return value if isinstance(value, dict) else {"type": "__invalid__"}

        async def send_message(payload: dict[str, Any]) -> None:
            await websocket.send_str(json.dumps(payload, separators=(",", ":")))

        normalized = HTTPRequest(
            method="GET",
            path=handler.endpoints.path,
            headers=request.headers,
            query_params=request.query,
            native_request=request,
            app=request.app,
            state=request,
        )
        await websocket_handler.handle(receive_message, send_message, request=normalized)
        return websocket

    for route_path in handler.endpoints.routes:
        view = make_view(route_path)
        application.router.add_get(route_path, view)
        if route_path == handler.endpoints.path:
            application.router.add_post(route_path, view)
            application.router.add_route("OPTIONS", route_path, view)
    return application


__all__ = ["create_aiohttp_app"]
