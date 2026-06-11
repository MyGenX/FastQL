"""Starlette-native FastQL router integration."""

from __future__ import annotations

from typing import Any

try:
    from starlette.requests import Request
    from starlette.responses import Response, StreamingResponse
    from starlette.routing import Route, Router, WebSocketRoute
    from starlette.websockets import WebSocket, WebSocketDisconnect
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError(
        "The Starlette adapter requires 'mygenx-fastql[starlette]'."
    ) from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)


def create_starlette_router(
    schema: Any,
    *,
    path: str = "/graphql",
    name: str = "fastql",
    **options: Any,
) -> Router:
    """Create a Starlette router exposing FastQL routes."""

    handler = GraphQLHTTPHandler(schema, path=path, **options)
    websocket_handler = GraphQLTransportWSHandler(handler)
    routes = []
    for index, route_path in enumerate(handler.endpoints.routes):
        methods = (
            ["GET", "POST", "OPTIONS"]
            if route_path == handler.endpoints.path
            else ["GET", "OPTIONS"]
        )

        async def endpoint(request: Request, target_path: str = route_path) -> Response:
            normalized = HTTPRequest(
                method=request.method,
                path=target_path,
                headers=request.headers,
                query_params=request.query_params,
                body=await request.body(),
                native_request=request,
                app=request.app,
                state=request.state,
            )
            result = await handler.handle(normalized)
            if result.is_streaming:
                return StreamingResponse(
                    result.body,
                    status_code=result.status,
                    headers=result.headers,
                )
            return Response(
                content=result.body,
                status_code=result.status,
                headers=result.headers,
            )

        route_name = name if route_path == handler.endpoints.path else f"{name}_{index}"
        routes.append(Route(route_path, endpoint, methods=methods, name=route_name))

    async def websocket_endpoint(websocket: WebSocket) -> None:
        protocols = websocket.scope.get("subprotocols", [])
        if GRAPHQL_TRANSPORT_WS_PROTOCOL not in protocols:
            await websocket.close(code=4406)
            return
        await websocket.accept(subprotocol=GRAPHQL_TRANSPORT_WS_PROTOCOL)

        async def receive_message():
            try:
                return await websocket.receive_json()
            except WebSocketDisconnect:
                return None

        request = HTTPRequest(
            method="GET",
            path=handler.endpoints.path,
            headers=websocket.headers,
            query_params=websocket.query_params,
            native_request=websocket,
            app=websocket.app,
            state=websocket.state,
        )
        await websocket_handler.handle(
            receive_message,
            websocket.send_json,
            request=request,
        )

    routes.append(
        WebSocketRoute(
            handler.endpoints.path,
            websocket_endpoint,
            name=f"{name}_websocket",
        )
    )
    return Router(routes=routes)


__all__ = ["create_starlette_router"]
