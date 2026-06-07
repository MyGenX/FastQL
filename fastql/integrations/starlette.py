"""Starlette-native FastQL router integration."""

from __future__ import annotations

from typing import Any

try:
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Route, Router
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError(
        "The Starlette adapter requires 'fastql[starlette]'."
    ) from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest


def create_starlette_router(
    schema: Any,
    *,
    path: str = "/graphql",
    name: str = "fastql",
    **options: Any,
) -> Router:
    """Create a Starlette router exposing FastQL routes."""

    handler = GraphQLHTTPHandler(schema, path=path, **options)
    routes = []
    for index, route_path in enumerate(handler.endpoints.routes):
        methods = ["GET", "POST", "OPTIONS"] if route_path == handler.endpoints.path else ["GET", "OPTIONS"]

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
            return Response(
                content=result.body,
                status_code=result.status,
                headers=result.headers,
            )

        route_name = name if route_path == handler.endpoints.path else f"{name}_{index}"
        routes.append(Route(route_path, endpoint, methods=methods, name=route_name))
    return Router(routes=routes)


__all__ = ["create_starlette_router"]
