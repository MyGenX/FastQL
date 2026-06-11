"""FastAPI-native FastQL router integration."""

from __future__ import annotations

from typing import Any, Sequence

try:
    from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
    from fastapi.params import Depends
    from starlette.responses import StreamingResponse
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError("The FastAPI adapter requires 'mygenx-fastql[fastapi]'.") from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)


def create_fastapi_router(
    schema: Any,
    *,
    path: str = "/graphql",
    dependencies: Sequence[Depends] | None = None,
    tags: list[str] | None = None,
    include_in_schema: bool = True,
    **options: Any,
) -> APIRouter:
    """Create an ``APIRouter`` that exposes FastQL endpoints."""

    router = APIRouter(
        dependencies=list(dependencies or []),
        tags=tags,
        include_in_schema=include_in_schema,
    )
    handler = GraphQLHTTPHandler(schema, path=path, **options)
    websocket_handler = GraphQLTransportWSHandler(handler)

    def make_endpoint(target_path: str):
        async def endpoint(request: Request) -> Response:
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

        endpoint.__name__ = f"fastql_{target_path.strip('/').replace('/', '_') or 'root'}"
        return endpoint

    for route_path in handler.endpoints.routes:
        methods = (
            ["GET", "POST", "OPTIONS"]
            if route_path == handler.endpoints.path
            else ["GET", "OPTIONS"]
        )
        router.add_api_route(
            route_path,
            make_endpoint(route_path),
            methods=methods,
            include_in_schema=include_in_schema,
            name="fastql" if route_path == handler.endpoints.path else None,
        )

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

    router.add_api_websocket_route(
        handler.endpoints.path,
        websocket_endpoint,
        name="fastql_websocket",
    )
    return router


__all__ = ["create_fastapi_router"]
