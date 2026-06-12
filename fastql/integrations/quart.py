"""Quart-native FastQL blueprint integration."""

from __future__ import annotations

import json
from typing import Any

try:
    from quart import Blueprint, Response, current_app, g, request, websocket
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError("The Quart adapter requires 'mygenx-fastql[quart]'.") from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)


def create_quart_blueprint(
    schema: Any,
    *,
    path: str = "/graphql",
    name: str = "fastql",
    import_name: str = __name__,
    **options: Any,
) -> "Blueprint":
    """Create a Quart blueprint exposing FastQL endpoints."""

    blueprint = Blueprint(name, import_name)
    handler = GraphQLHTTPHandler(schema, path=path, **options)
    websocket_handler = GraphQLTransportWSHandler(handler)

    def make_view(target_path: str):
        async def view() -> Response:
            normalized = HTTPRequest(
                method=request.method,
                path=target_path,
                headers=request.headers,
                query_params=request.args,
                body=await request.get_data(),
                native_request=request,
                app=current_app,
                state=g,
            )
            result = await handler.handle(normalized)
            return Response(
                result.body,
                status=result.status,
                headers=dict(result.headers),
            )

        return view

    for index, route_path in enumerate(handler.endpoints.routes):
        methods = (
            ["GET", "POST", "OPTIONS"]
            if route_path == handler.endpoints.path
            else ["GET", "OPTIONS"]
        )
        endpoint = name if route_path == handler.endpoints.path else f"{name}_{index}"
        blueprint.add_url_rule(
            route_path,
            endpoint=endpoint,
            view_func=make_view(route_path),
            methods=methods,
        )

    async def websocket_view() -> None:
        await websocket.accept(subprotocol=GRAPHQL_TRANSPORT_WS_PROTOCOL)

        async def receive_message():
            raw_message = await websocket.receive()
            try:
                value = json.loads(raw_message)
            except (json.JSONDecodeError, TypeError):
                return {"type": "__invalid__"}
            return value if isinstance(value, dict) else {"type": "__invalid__"}

        async def send_message(payload: dict[str, Any]) -> None:
            await websocket.send(json.dumps(payload, separators=(",", ":")))

        normalized = HTTPRequest(
            method="GET",
            path=handler.endpoints.path,
            headers=websocket.headers,
            query_params=websocket.args,
            native_request=websocket,
            app=current_app,
            state=g,
        )
        await websocket_handler.handle(receive_message, send_message, request=normalized)

    blueprint.add_websocket(
        handler.endpoints.path,
        f"{name}_websocket",
        websocket_view,
    )
    return blueprint


__all__ = ["create_quart_blueprint"]
