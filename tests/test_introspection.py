"""Introspection tests covering the introspection OpenSpec scenarios."""

import pytest

from fastql.decorators import default_registry
from fastql.execution import execute
from fastql.schema_builder import build_schema
from fastql.types import (
    Argument,
    Boolean,
    Field,
    ID,
    Int,
    NonNull,
    ObjectType,
    String,
)


@pytest.fixture(autouse=True)
def clear_registry():
    default_registry.clear()


def make_schema():
    user = ObjectType(
        "User",
        fields={"id": Field(NonNull(ID)), "name": Field(String)},
    )

    def resolve_user(id):
        return {"id": id, "name": "Ada"}

    query = ObjectType(
        "Query",
        fields={
            "user": Field(
                user, args={"id": Argument(NonNull(ID))}, resolver=resolve_user
            )
        },
    )
    return build_schema(query=query)


async def test_schema_type_listing():
    result = await execute(make_schema(), "{ __schema { types { name kind } } }")

    assert result.errors == []
    type_entries = result.data["__schema"]["types"]
    by_name = {t["name"]: t["kind"] for t in type_entries}
    assert by_name["User"] == "OBJECT"
    assert by_name["Query"] == "OBJECT"
    assert by_name["ID"] == "SCALAR"


async def test_schema_root_types():
    result = await execute(
        make_schema(),
        "{ __schema { queryType { name } directives { name } } }",
    )
    assert result.data["__schema"]["queryType"]["name"] == "Query"
    directive_names = {d["name"] for d in result.data["__schema"]["directives"]}
    assert {"skip", "include", "deprecated"} <= directive_names


async def test_type_lookup_by_name():
    result = await execute(
        make_schema(),
        '{ __type(name: "User") { name kind fields { name } } }',
    )

    assert result.errors == []
    type_info = result.data["__type"]
    assert type_info["name"] == "User"
    assert type_info["kind"] == "OBJECT"
    field_names = {f["name"] for f in type_info["fields"]}
    assert field_names == {"id", "name"}


async def test_type_lookup_unknown_returns_null():
    result = await execute(make_schema(), '{ __type(name: "Ghost") { name } }')
    assert result.data == {"__type": None}


async def test_field_type_is_introspectable():
    result = await execute(
        make_schema(),
        '{ __type(name: "User") { fields { name type { kind ofType { name } } } } }',
    )
    fields = {f["name"]: f for f in result.data["__type"]["fields"]}
    # `id` is ID! -> NON_NULL wrapping the ID scalar.
    assert fields["id"]["type"]["kind"] == "NON_NULL"
    assert fields["id"]["type"]["ofType"]["name"] == "ID"


async def test_typename_on_a_selection():
    result = await execute(make_schema(), '{ user(id: "1") { __typename id } }')
    assert result.data == {"user": {"__typename": "User", "id": "1"}}


async def test_typename_on_query_root():
    result = await execute(make_schema(), "{ __typename }")
    assert result.data == {"__typename": "Query"}


async def test_deprecated_default_value_is_graphql_literal():
    # Regression: defaultValue must be a GraphQL value literal, not the raw
    # Python string. The @deprecated reason default "No longer supported" was
    # emitted unquoted, which broke GraphiQL's introspection parsing with
    # `Syntax Error: Expected <EOF>, found Name "longer"`.
    result = await execute(
        make_schema(),
        "{ __schema { directives { name args { name defaultValue } } } }",
    )
    assert result.errors == []
    directives = {d["name"]: d for d in result.data["__schema"]["directives"]}
    reason_arg = next(
        a for a in directives["deprecated"]["args"] if a["name"] == "reason"
    )
    assert reason_arg["defaultValue"] == '"No longer supported"'


async def test_argument_default_values_are_graphql_literals():
    query = ObjectType(
        "Query",
        fields={
            "search": Field(
                String,
                args={
                    "term": Argument(String, default_value="hi"),
                    "limit": Argument(Int, default_value=10),
                    "exact": Argument(Boolean, default_value=False),
                },
                resolver=lambda **kwargs: "ok",
            )
        },
    )
    schema = build_schema(query=query)
    result = await execute(
        schema,
        '{ __type(name: "Query") { fields { args { name defaultValue } } } }',
    )
    assert result.errors == []
    args = {
        a["name"]: a["defaultValue"]
        for f in result.data["__type"]["fields"]
        for a in f["args"]
    }
    assert args["term"] == '"hi"'
    assert args["limit"] == "10"
    assert args["exact"] == "false"
