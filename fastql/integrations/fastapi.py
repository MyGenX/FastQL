"""FastAPI-native FastQL router integration."""

from __future__ import annotations

from typing import Any, Sequence

try:
    from fastapi import APIRouter, Request, Response
    from fastapi.params import Depends
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError("The FastAPI adapter requires 'fastql[fastapi]'.") from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest


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
            return Response(
                content=result.body,
                status_code=result.status,
                headers=result.headers,
            )

        endpoint.__name__ = f"fastql_{target_path.strip('/').replace('/', '_') or 'root'}"
        return endpoint

    for route_path in handler.endpoints.routes:
        methods = ["GET", "POST", "OPTIONS"] if route_path == handler.endpoints.path else ["GET", "OPTIONS"]
        router.add_api_route(
            route_path,
            make_endpoint(route_path),
            methods=methods,
            include_in_schema=include_in_schema,
            name="fastql" if route_path == handler.endpoints.path else None,
        )
    return router


__all__ = ["create_fastapi_router"]
