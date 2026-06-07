"""Contract tests for the shared GraphQL-over-HTTP handler."""

from __future__ import annotations

import json

from fastql.integrations import GraphQLHTTPHandler, HTTPContext, HTTPRequest
from fastql.registry import TypeRegistry
from fastql.schema_builder import build_schema
from fastql.types import Field, NonNull, ObjectType, String


def make_schema():
    query = ObjectType(
        "Query",
        fields={
            "ping": Field(NonNull(String), resolver=lambda: "pong"),
            "requestPath": Field(
                NonNull(String), resolver=lambda ctx: ctx.request.path
            ),
            "rootName": Field(String, resolver=lambda parent: parent.get("name")),
        },
    )
    mutation = ObjectType(
        "Mutation",
        fields={"touch": Field(NonNull(String), resolver=lambda: "done")},
    )
    return build_schema(query=query, mutation=mutation, registry=TypeRegistry())


def request(method="POST", path="/graphql", payload=None, **kwargs):
    headers = kwargs.pop("headers", {})
    body = b""
    if payload is not None:
        body = json.dumps(payload).encode()
        headers = {"content-type": "application/json", **headers}
    return HTTPRequest(method, path, headers=headers, body=body, **kwargs)


async def test_post_and_get_queries_share_result_contract():
    handler = GraphQLHTTPHandler(make_schema())
    post = await handler.handle(request(payload={"query": "{ ping }"}))
    get = await handler.handle(
        request("GET", query_params={"query": "{ ping }"})
    )
    assert post.status == get.status == 200
    assert json.loads(post.body) == json.loads(get.body) == {"data": {"ping": "pong"}}


async def test_transport_validation_and_get_operation_safety():
    handler = GraphQLHTTPHandler(make_schema())
    invalid_json = await handler.handle(
        HTTPRequest(
            "POST",
            "/graphql",
            headers={"content-type": "application/json"},
            body=b"{bad",
        )
    )
    unsupported = await handler.handle(
        HTTPRequest(
            "POST",
            "/graphql",
            headers={"content-type": "text/plain"},
            body=b"{ ping }",
        )
    )
    mutation = await handler.handle(
        request("GET", query_params={"query": "mutation { touch }"})
    )
    method = await handler.handle(request("DELETE"))
    assert invalid_json.status == 400
    assert unsupported.status == 415
    assert mutation.status == method.status == 405
    assert mutation.headers["allow"] == "POST"


async def test_payload_fields_are_typed_and_operation_name_is_forwarded():
    handler = GraphQLHTTPHandler(make_schema())
    invalid = await handler.handle(
        request(payload={"query": "{ ping }", "variables": []})
    )
    selected = await handler.handle(
        request(
            payload={
                "query": "query A { ping } query B { rootName }",
                "operationName": "A",
                "extensions": {"trace": True},
            }
        )
    )
    assert invalid.status == 400
    assert json.loads(selected.body) == {"data": {"ping": "pong"}}


async def test_graphql_errors_remain_graphql_results():
    handler = GraphQLHTTPHandler(make_schema())
    response = await handler.handle(request(payload={"query": "{ missing }"}))
    assert response.status == 200
    assert "errors" in json.loads(response.body)


async def test_context_factory_root_value_and_response_control():
    seen = []

    async def context_factory(context: HTTPContext):
        seen.append(context)
        context.response.set_header("x-fastql", "active")

    handler = GraphQLHTTPHandler(
        make_schema(), context_factory=context_factory, root_value={"name": "root"}
    )
    response = await handler.handle(
        request(payload={"query": "{ requestPath rootName }"})
    )
    assert json.loads(response.body)["data"] == {
        "requestPath": "/graphql",
        "rootName": "root",
    }
    assert response.headers["x-fastql"] == "active"
    assert len(seen) == 1


async def test_context_replacement_and_zero_argument_factory_are_supported():
    query = ObjectType(
        "Query",
        fields={"legacy": Field(NonNull(String), resolver=lambda ctx: str(ctx["legacy"]))},
    )
    handler = GraphQLHTTPHandler(
        build_schema(query=query, registry=TypeRegistry()),
        context_factory=lambda: {"legacy": True},
    )
    response = await handler.handle(request(payload={"query": "{ legacy }"}))
    assert json.loads(response.body) == {"data": {"legacy": "True"}}


async def test_companion_endpoints_are_configurable_and_negotiated():
    handler = GraphQLHTTPHandler(
        make_schema(),
        graphiql=True,
        schema_path="/schema.graphql",
        introspection_path="/schema.json",
    )
    graphiql = await handler.handle(
        request("GET", headers={"accept": "text/html"})
    )
    sdl = await handler.handle(request("GET", "/schema.graphql"))
    introspection = await handler.handle(request("GET", "/schema.json"))
    assert graphiql.status == 200 and b"GraphiQL" in graphiql.body
    assert b"type Query" in sdl.body
    assert "__schema" in json.loads(introspection.body)["data"]

    disabled = GraphQLHTTPHandler(make_schema())
    assert (await disabled.handle(request("GET", "/schema.graphql"))).status == 404


async def test_response_media_type_negotiation():
    handler = GraphQLHTTPHandler(make_schema())
    response = await handler.handle(
        request(
            payload={"query": "{ ping }"},
            headers={"accept": "application/graphql-response+json"},
        )
    )
    assert response.headers["content-type"] == "application/graphql-response+json"


def test_request_models_validate_and_response_controls_are_isolated():
    first = HTTPContext(request=object())
    second = HTTPContext(request=object())
    first.response.set_header("x-one", "1")
    assert second.response.headers == {}

    try:
        HTTPRequest("POST", "/", body="not-bytes")
    except TypeError as error:
        assert "bytes" in str(error)
    else:  # pragma: no cover
        raise AssertionError("non-byte request body was accepted")
