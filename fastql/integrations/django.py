"""Django-native FastQL view and URL helpers."""

from __future__ import annotations

from typing import Any

try:
    from django.http import HttpRequest, HttpResponse
    from django.urls import path as django_path
    from django.views import View
    from django.views.decorators.csrf import csrf_exempt as csrf_exempt_decorator
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError("The Django adapter requires 'mygenx-fastql[django]'.") from error

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest


class FastQLView(View):
    """Async-capable Django class-based view backed by the shared handler."""

    schema: Any = None
    handler_options: dict[str, Any] | None = None
    target_path: str = "/graphql"
    http_method_names = ["get", "post", "options"]

    async def _handle(self, request: HttpRequest) -> HttpResponse:
        options = dict(self.handler_options or {})
        handler = GraphQLHTTPHandler(self.schema, **options)
        normalized = HTTPRequest(
            method=request.method,
            path=self.target_path,
            headers=request.headers,
            query_params=request.GET,
            body=request.body,
            native_request=request,
            app=None,
            state=request,
        )
        result = await handler.handle(normalized)
        response = HttpResponse(
            content=result.body,
            status=result.status,
            content_type=result.headers.pop("content-type", None),
        )
        for key, value in result.headers.items():
            response[key] = value
        return response

    async def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return await self._handle(request)

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return await self._handle(request)

    async def options(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return await self._handle(request)


def create_django_view(
    schema: Any,
    *,
    target_path: str = "/graphql",
    csrf_exempt: bool = False,
    **handler_options: Any,
):
    """Create a configured Django view callable."""

    view = FastQLView.as_view(
        schema=schema,
        handler_options=handler_options,
        target_path=target_path,
    )
    return csrf_exempt_decorator(view) if csrf_exempt else view


def create_django_urlpatterns(
    schema: Any,
    *,
    path: str = "/graphql",
    name: str = "fastql",
    csrf_exempt: bool = False,
    **options: Any,
) -> list[Any]:
    """Create URL patterns for every configured FastQL endpoint."""

    handler = GraphQLHTTPHandler(schema, path=path, **options)
    patterns = []
    for index, route_path in enumerate(handler.endpoints.routes):
        view = create_django_view(
            schema,
            target_path=route_path,
            csrf_exempt=csrf_exempt,
            path=path,
            **options,
        )
        route_name = name if route_path == handler.endpoints.path else f"{name}_{index}"
        patterns.append(django_path(route_path.lstrip("/"), view, name=route_name))
    return patterns


__all__ = ["FastQLView", "create_django_urlpatterns", "create_django_view"]
