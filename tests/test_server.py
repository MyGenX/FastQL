"""Dev-server tests: dispatcher routing, integration over sockets, and boundary."""

import asyncio
import json
import subprocess
import sys

import pytest

from fastql.decorators import default_registry
from fastql.schema_builder import build_schema
from fastql.server import _Dispatcher, start_server
from fastql.types import Argument, Field, Int, NonNull, ObjectType, String


@pytest.fixture(autouse=True)
def clear_registry():
    default_registry.clear()


def make_schema():
    query = ObjectType(
        "Query",
        fields={
            "ping": Field(NonNull(String), resolver=lambda: "pong"),
            "echo": Field(
                Int,
                args={"value": Argument(NonNull(Int))},
                resolver=lambda value: value,
            ),
        },
    )
    return build_schema(query=query)


# --- dispatcher routing ------------------------------------------------------


async def test_post_query_returns_data():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("POST", "/graphql", {}, b'{"query":"{ ping }"}')
    assert r.status == 200
    assert json.loads(r.body) == {"data": {"ping": "pong"}}


async def test_get_query_works():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("GET", "/graphql", {"query": "{ ping }"}, b"")
    assert json.loads(r.body)["data"]["ping"] == "pong"


async def test_variables_are_forwarded():
    d = _Dispatcher(make_schema(), "/graphql")
    body = json.dumps(
        {"query": "query($v: Int!){ echo(value: $v) }", "variables": {"v": 41}}
    ).encode()
    r = await d.dispatch("POST", "/graphql", {}, body)
    assert json.loads(r.body)["data"] == {"echo": 41}


async def test_malformed_json_is_400():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("POST", "/graphql", {}, b"{ not json")
    assert r.status == 400


async def test_unknown_path_is_404():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("GET", "/nope", {}, b"")
    assert r.status == 404


async def test_wrong_method_is_405():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("POST", "/", {}, b"")
    assert r.status == 405


async def test_graphql_error_stays_200():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("POST", "/graphql", {}, b'{"query":"{ nope }"}')
    assert r.status == 200
    assert "errors" in json.loads(r.body)


async def test_playground_served_at_root():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("GET", "/", {}, b"")
    assert r.status == 200
    assert "graphiql" in r.body.lower()
    assert "/graphql" in r.body


async def test_playground_reflects_custom_path():
    d = _Dispatcher(make_schema(), "/api/graphql")
    r = await d.dispatch("GET", "/", {}, b"")
    assert "/api/graphql" in r.body


async def test_schema_graphql_endpoint():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("GET", "/schema.graphql", {}, b"")
    assert r.status == 200
    assert "text/plain" in r.content_type
    assert "type Query" in r.body


async def test_schema_json_endpoint():
    d = _Dispatcher(make_schema(), "/graphql")
    r = await d.dispatch("GET", "/schema.json", {}, b"")
    assert r.status == 200
    data = json.loads(r.body)["data"]
    assert data["__schema"]["queryType"]["name"] == "Query"


async def test_context_factory_injects_context_into_resolvers():
    user = ObjectType("User", fields={"name": Field(String)})

    def resolve(id, ctx):  # `ctx` is injected as the Context
        return ctx["users"].get(id)

    query = ObjectType(
        "Query",
        fields={
            "u": Field(user, args={"id": Argument(NonNull(Int))}, resolver=resolve)
        },
    )
    d = _Dispatcher(
        build_schema(query=query),
        "/graphql",
        context_factory=lambda: {"users": {1: {"name": "Ada"}}},
    )
    r = await d.dispatch("POST", "/graphql", {}, b'{"query":"{ u(id: 1){ name } }"}')
    assert json.loads(r.body)["data"] == {"u": {"name": "Ada"}}


async def test_example_user_resolves_via_fallback_store():
    from examples.hello import schema

    d = _Dispatcher(schema, "/graphql")
    r = await d.dispatch(
        "POST", "/graphql", {}, b'{"query":"{ user(id: 1){ id name } }"}'
    )
    assert json.loads(r.body)["data"]["user"] == {"id": 1, "name": "Ada Lovelace"}


# --- socket integration ------------------------------------------------------


async def _http_request(host, port, method, path, body=None):
    reader, writer = await asyncio.open_connection(host, port)
    body_bytes = body.encode() if isinstance(body, str) else (body or b"")
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host}"]
    if body_bytes:
        lines += ["Content-Type: application/json", f"Content-Length: {len(body_bytes)}"]
    request = ("\r\n".join(lines) + "\r\n\r\n").encode() + body_bytes
    writer.write(request)
    await writer.drain()
    raw = await reader.read()
    writer.close()
    head, _, payload = raw.partition(b"\r\n\r\n")
    status = int(head.split(b" ")[1])
    return status, payload.decode()


async def test_server_routes_over_sockets():
    server = await start_server(make_schema(), host="127.0.0.1", port=0)
    host, port = server.sockets[0].getsockname()[:2]
    try:
        status, body = await _http_request(host, port, "POST", "/graphql", '{"query":"{ ping }"}')
        assert status == 200 and "pong" in body

        status, body = await _http_request(host, port, "GET", "/")
        assert status == 200 and "graphiql" in body.lower()

        status, body = await _http_request(host, port, "GET", "/schema.graphql")
        assert status == 200 and "type Query" in body

        status, body = await _http_request(host, port, "GET", "/schema.json")
        assert status == 200 and "__schema" in body
    finally:
        server.close()
        await server.wait_closed()


async def test_default_binding_uses_127_0_0_1_and_7691():
    try:
        server = await start_server(make_schema())
    except OSError:
        pytest.skip("default port 7691 is unavailable in this environment")
    try:
        host, port = server.sockets[0].getsockname()[:2]
        assert host == "127.0.0.1"
        assert port == 7691
    finally:
        server.close()
        await server.wait_closed()


# --- agnostic-core boundary --------------------------------------------------


def test_core_does_not_import_server():
    code = (
        "import fastql.execution, fastql.schema_builder, fastql.types, fastql.context; "
        "import sys; "
        "assert 'fastql.server' not in sys.modules, 'core imported fastql.server'; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
