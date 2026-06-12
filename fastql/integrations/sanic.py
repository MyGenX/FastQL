"""Sanic-native FastQL blueprint integration.

Sanic does not allow an HTTP ``GET`` route and a WebSocket route to share a URI,
so this adapter exposes the HTTP endpoints (queries, mutations, GraphiQL, file
uploads, batching) and serves subscriptions over the SSE / ``multipart`` HTTP
transports rather than a same-path ``graphql-transport-ws`` socket.
"""

from __future__ import annotations

from typing import Any

try:
    from sanic import Blueprint
    from sanic.response import ResponseStream, raw
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError("The Sanic adapter requires 'mygenx-fastql[sanic]'.") from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest


def create_sanic_blueprint(
    schema: Any,
    *,
    path: str = "/graphql",
    name: str = "fastql",
    **options: Any,
) -> "Blueprint":
    """Create a Sanic blueprint exposing FastQL endpoints."""

    blueprint = Blueprint(name)
    handler = GraphQLHTTPHandler(schema, path=path, **options)

    def make_view(target_path: str):
        async def view(request: Any) -> Any:
            normalized = HTTPRequest(
                method=request.method,
                path=target_path,
                headers=request.headers,
                query_params=request.args,
                body=request.body or b"",
                native_request=request,
                app=request.app,
                state=request.ctx,
            )
            result = await handler.handle(normalized)
            headers = dict(result.headers)
            content_type = headers.pop("content-type", "application/json")
            if result.is_streaming:
                async def stream(response: Any) -> None:
                    async for chunk in result.body:
                        await response.write(chunk)

                return ResponseStream(
                    stream,
                    status=result.status,
                    headers=headers,
                    content_type=content_type,
                )
            return raw(
                result.body,
                status=result.status,
                headers=headers,
                content_type=content_type,
            )

        return view

    for index, route_path in enumerate(handler.endpoints.routes):
        methods = (
            ["GET", "POST", "OPTIONS"]
            if route_path == handler.endpoints.path
            else ["GET", "OPTIONS"]
        )
        blueprint.add_route(
            make_view(route_path),
            route_path,
            methods=methods,
            name=name if route_path == handler.endpoints.path else f"{name}_{index}",
        )

    return blueprint


__all__ = ["create_sanic_blueprint"]
