"""Framework-native adapter tests, enabled when each optional extra is installed."""

from __future__ import annotations

import asyncio
import json

import pytest

from fastql.registry import TypeRegistry
from fastql.schema_builder import build_schema
from fastql.types import Field, NonNull, ObjectType, String
from fastql.integrations.websocket import GRAPHQL_TRANSPORT_WS_PROTOCOL


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


def make_subscription_schema():
    async def events():
        yield "ready"

    query = ObjectType(
        "Query", fields={"ping": Field(NonNull(String), resolver=lambda: "pong")}
    )
    subscription = ObjectType(
        "Subscription",
        fields={"events": Field(NonNull(String), resolver=events)},
    )
    return build_schema(
        query=query,
        subscription=subscription,
        registry=TypeRegistry(),
    )


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


def test_starlette_router_exposes_graphql_transport_websocket():
    pytest.importorskip("starlette")
    pytest.importorskip("httpx")
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.testclient import TestClient

    from fastql.integrations.starlette import create_starlette_router

    app = Starlette(
        routes=[Mount("/api", app=create_starlette_router(make_subscription_schema()))]
    )
    with TestClient(app) as client:
        with client.websocket_connect(
            "/api/graphql", subprotocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL]
        ) as websocket:
            websocket.send_json({"type": "connection_init"})
            assert websocket.receive_json() == {"type": "connection_ack"}
            websocket.send_json(
                {
                    "id": "events",
                    "type": "subscribe",
                    "payload": {"query": "subscription { events }"},
                }
            )
            assert websocket.receive_json()["payload"] == {
                "data": {"events": "ready"}
            }
            assert websocket.receive_json() == {
                "id": "events",
                "type": "complete",
            }


def test_fastapi_router_exposes_graphql_transport_websocket():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from fastql.integrations.fastapi import create_fastapi_router

    app = FastAPI()
    app.include_router(
        create_fastapi_router(make_subscription_schema()), prefix="/api"
    )
    with TestClient(app) as client:
        with client.websocket_connect(
            "/api/graphql", subprotocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL]
        ) as websocket:
            websocket.send_json({"type": "connection_init"})
            assert websocket.receive_json() == {"type": "connection_ack"}
            websocket.send_json(
                {
                    "id": "events",
                    "type": "subscribe",
                    "payload": {"query": "subscription { events }"},
                }
            )
            assert websocket.receive_json()["payload"] == {
                "data": {"events": "ready"}
            }
            assert websocket.receive_json() == {
                "id": "events",
                "type": "complete",
            }


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


# -- additional framework adapters (Phase 4) ---------------------------------


@pytest.mark.parametrize(
    "module, extra",
    [
        ("aiohttp", "aiohttp"),
        ("sanic", "sanic"),
        ("litestar", "litestar"),
        ("quart", "quart"),
        ("channels", "channels"),
    ],
)
def test_additional_adapter_names_its_extra_when_missing(module, extra):
    """When the framework is absent, importing the adapter names its extra."""
    try:
        __import__(module)
    except ImportError:
        with pytest.raises(ImportError, match=rf"mygenx-fastql\[{extra}\]"):
            __import__(f"fastql.integrations.{module}")
    else:  # framework installed — the adapter module imports cleanly
        __import__(f"fastql.integrations.{module}")


@pytest.mark.asyncio
async def test_aiohttp_app_get_post_and_graphiql():
    pytest.importorskip("aiohttp")
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    from fastql.integrations.aiohttp import create_aiohttp_app

    app = create_aiohttp_app(make_schema(), graphiql=True)

    @web.middleware
    async def state_middleware(request, handler):
        request["fastql_name"] = "aiohttp"
        return await handler(request)

    app.middlewares.append(state_middleware)
    async with TestClient(TestServer(app)) as client:
        post = await client.post("/graphql", json={"query": "{ ping framework }"})
        post_body = await post.json()
        page = await client.get("/graphql", headers={"accept": "text/html"})
        page_body = await page.text()
    assert post_body["data"] == {"ping": "pong", "framework": "aiohttp"}
    assert "<!DOCTYPE html>" in page_body or "graphiql" in page_body.lower()


def test_sanic_blueprint_get_post_and_graphiql():
    pytest.importorskip("sanic")
    pytest.importorskip("sanic_testing")
    from sanic import Sanic
    from sanic_testing import TestManager

    from fastql.integrations.sanic import create_sanic_blueprint

    app = Sanic("fastql_test")

    @app.on_request
    async def identify(request):
        request.ctx.fastql_name = "sanic"

    app.blueprint(create_sanic_blueprint(make_schema(), graphiql=True))
    TestManager(app)

    _, post = app.test_client.post("/graphql", json={"query": "{ ping framework }"})
    _, page = app.test_client.get("/graphql", headers={"accept": "text/html"})
    assert post.json["data"] == {"ping": "pong", "framework": "sanic"}
    assert page.status == 200


def test_litestar_router_get_post_and_graphiql():
    pytest.importorskip("litestar")
    from litestar import Litestar
    from litestar.testing import TestClient

    from fastql.integrations.litestar import create_litestar_router

    app = Litestar(route_handlers=[create_litestar_router(make_schema(), graphiql=True)])
    with TestClient(app=app) as client:
        post = client.post("/graphql", json={"query": "{ ping }"})
        page = client.get("/graphql", headers={"accept": "text/html"})
    assert post.json()["data"] == {"ping": "pong"}
    assert page.status_code == 200


@pytest.mark.asyncio
async def test_quart_blueprint_get_post_and_graphiql():
    pytest.importorskip("quart")
    from quart import Quart, g

    from fastql.integrations.quart import create_quart_blueprint

    app = Quart(__name__)

    @app.before_request
    def identify():
        g.fastql_name = "quart"

    app.register_blueprint(
        create_quart_blueprint(make_schema(), graphiql=True), url_prefix="/api"
    )
    client = app.test_client()
    post = await client.post("/api/graphql", json={"query": "{ ping framework }"})
    post_body = await post.get_json()
    page = await client.get("/api/graphql", headers={"accept": "text/html"})
    assert post_body["data"] == {"ping": "pong", "framework": "quart"}
    assert page.status_code == 200


@pytest.mark.asyncio
async def test_channels_consumer_drives_graphql_transport_ws():
    pytest.importorskip("channels")
    # channels.testing eagerly imports daphne (via ChannelsLiveServerTestCase),
    # which is a separate optional dependency the adapter itself does not need.
    pytest.importorskip("daphne")
    _configure_django()
    from channels.testing import WebsocketCommunicator

    from fastql.integrations.channels import create_graphql_consumer

    consumer = create_graphql_consumer(make_subscription_schema())
    communicator = WebsocketCommunicator(
        consumer.as_asgi(),
        "/graphql",
        subprotocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL],
    )
    communicator.scope["subprotocols"] = [GRAPHQL_TRANSPORT_WS_PROTOCOL]
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"type": "connection_init"})
    assert (await communicator.receive_json_from())["type"] == "connection_ack"
    await communicator.send_json_to(
        {
            "id": "events",
            "type": "subscribe",
            "payload": {"query": "subscription { events }"},
        }
    )
    assert (await communicator.receive_json_from())["payload"] == {
        "data": {"events": "ready"}
    }
    await communicator.disconnect()
