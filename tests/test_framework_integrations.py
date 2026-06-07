"""Framework-native adapter tests, enabled when each optional extra is installed."""

from __future__ import annotations

import asyncio
import json

import pytest

from fastql.registry import TypeRegistry
from fastql.schema_builder import build_schema
from fastql.types import Field, NonNull, ObjectType, String


async def test_sync_bridge_does_not_nest_a_running_event_loop():
    from fastql.integrations._sync import run_sync

    assert run_sync(asyncio.sleep(0, result="complete")) == "complete"


def make_schema():
    query = ObjectType(
        "Query",
        fields={
            "ping": Field(NonNull(String), resolver=lambda: "pong"),
            "framework": Field(
                NonNull(String),
                resolver=lambda ctx: ctx.state.fastql_name
                if hasattr(ctx.state, "fastql_name")
                else ctx.state["fastql_name"],
            ),
        },
    )
    return build_schema(query=query, registry=TypeRegistry())


def test_starlette_router_mount_middleware_context_and_schema_route():
    starlette = pytest.importorskip("starlette")
    pytest.importorskip("httpx")
    from starlette.applications import Starlette
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.routing import Mount
    from starlette.testclient import TestClient

    from fastql.integrations.starlette import create_starlette_router

    class StateMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.fastql_name = "starlette"
            return await call_next(request)

    router = create_starlette_router(
        make_schema(), schema_path="/schema.graphql", graphiql=True
    )
    app = Starlette(routes=[Mount("/api", app=router)])
    app.add_middleware(StateMiddleware)
    with TestClient(app) as client:
        response = client.post(
            "/api/graphql", json={"query": "{ ping framework }"}
        )
        schema = client.get("/api/schema.graphql")
    assert response.json()["data"] == {
        "ping": "pong",
        "framework": "starlette",
    }
    assert "type Query" in schema.text
    assert starlette is not None


def test_fastapi_router_dependencies_prefix_and_openapi_controls():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi import Depends, FastAPI, Request
    from fastapi.testclient import TestClient

    from fastql.integrations.fastapi import create_fastapi_router

    async def identify(request: Request):
        request.state.fastql_name = "fastapi"

    identify.__annotations__["request"] = Request

    router = create_fastapi_router(
        make_schema(),
        dependencies=[Depends(identify)],
        tags=["GraphQL"],
        include_in_schema=False,
    )
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        response = client.post(
            "/api/graphql", json={"query": "{ ping framework }"}
        )
        openapi = client.get("/openapi.json").json()
    assert response.json()["data"]["framework"] == "fastapi"
    assert "/api/graphql" not in openapi["paths"]


def test_flask_blueprint_prefix_hooks_headers_and_async_execution():
    flask = pytest.importorskip("flask")
    from flask import Flask, g

    from fastql.integrations.flask import create_flask_blueprint

    async def context_factory(context):
        context.response.set_header("x-fastql", "flask")
        return context

    app = Flask(__name__)

    @app.before_request
    def identify():
        g.fastql_name = "flask"

    app.register_blueprint(
        create_flask_blueprint(make_schema(), context_factory=context_factory),
        url_prefix="/api",
    )
    with app.test_client() as client:
        response = client.post(
            "/api/graphql", json={"query": "{ ping framework }"}
        )
    assert response.get_json()["data"]["framework"] == "flask"
    assert response.headers["x-fastql"] == "flask"
    assert flask is not None


def _configure_django():
    django = pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="fastql-tests",
            ROOT_URLCONF=__name__,
            ALLOWED_HOSTS=["testserver"],
            MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        )
        django.setup()
    return django


def test_django_urlpatterns_context_and_csrf_configuration():
    _configure_django()
    from fastql.integrations.django import create_django_urlpatterns, create_django_view

    patterns = create_django_urlpatterns(
        make_schema(), schema_path="/schema.graphql"
    )
    assert {pattern.name for pattern in patterns} >= {"fastql"}

    secure_view = create_django_view(make_schema(), path="/graphql")
    exempt_view = create_django_view(
        make_schema(), path="/graphql", csrf_exempt=True
    )
    assert not getattr(secure_view, "csrf_exempt", False)
    assert getattr(exempt_view, "csrf_exempt", False)


@pytest.mark.asyncio
async def test_django_async_view_executes_with_request_state():
    _configure_django()
    from django.test import AsyncRequestFactory

    from fastql.integrations.django import create_django_view

    request = AsyncRequestFactory().post(
        "/graphql",
        data=json.dumps({"query": "{ ping framework }"}),
        content_type="application/json",
    )
    request.fastql_name = "django"
    view = create_django_view(make_schema(), path="/graphql")
    response = await view(request)
    assert json.loads(response.content)["data"] == {
        "ping": "pong",
        "framework": "django",
    }
