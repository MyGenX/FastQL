"""Flask-native FastQL blueprint integration."""

from __future__ import annotations

from typing import Any

try:
    from flask import Blueprint, Response, current_app, g, request
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError("The Flask adapter requires 'fastql[flask]'.") from error

from fastql.integrations._sync import run_sync
from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest


def create_flask_blueprint(
    schema: Any,
    *,
    path: str = "/graphql",
    name: str = "fastql",
    import_name: str = __name__,
    **options: Any,
) -> Blueprint:
    """Create a Flask blueprint exposing FastQL endpoints."""

    blueprint = Blueprint(name, import_name)
    handler = GraphQLHTTPHandler(schema, path=path, **options)

    def make_view(target_path: str):
        def view() -> Response:
            normalized = HTTPRequest(
                method=request.method,
                path=target_path,
                headers=request.headers,
                query_params=request.args,
                body=request.get_data(cache=True),
                native_request=request._get_current_object(),
                app=current_app._get_current_object(),
                state=g,
            )
            result = run_sync(handler.handle(normalized))
            return Response(
                response=result.body,
                status=result.status,
                headers=result.headers,
            )

        return view

    for index, route_path in enumerate(handler.endpoints.routes):
        methods = ["GET", "POST", "OPTIONS"] if route_path == handler.endpoints.path else ["GET", "OPTIONS"]
        endpoint = name if route_path == handler.endpoints.path else f"{name}_{index}"
        blueprint.add_url_rule(
            route_path,
            endpoint=endpoint,
            view_func=make_view(route_path),
            methods=methods,
        )
    return blueprint


__all__ = ["create_flask_blueprint"]
