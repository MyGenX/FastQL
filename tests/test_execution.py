"""Execution-engine tests covering the query-execution OpenSpec scenarios."""

import pytest

from fastql.errors import GraphQLError
from fastql.execution import execute
from fastql.types import (
    Argument,
    Field,
    ID,
    Int,
    ListType,
    NonNull,
    ObjectType,
    String,
)
from fastql.types.schema import Schema


def _user_type():
    return ObjectType(
        "User",
        fields={
            "id": Field(NonNull(ID)),
            "name": Field(String),
        },
    )


@pytest.fixture
def schema():
    user = _user_type()

    def resolve_user(id):
        return {"id": id, "name": f"User {id}"}

    async def resolve_async_name():
        return "async!"

    query = ObjectType(
        "Query",
        fields={
            "user": Field(
                user,
                args={"id": Argument(NonNull(ID))},
                resolver=resolve_user,
            ),
            "ping": Field(NonNull(String), resolver=lambda: "pong"),
            "asyncName": Field(String, resolver=resolve_async_name),
        },
    )
    return Schema(query)


async def test_successful_query(schema):
    result = await execute(schema, '{ user(id: "1") { id name } }')
    assert result.errors == []
    assert result.data == {"user": {"id": "1", "name": "User 1"}}


async def test_sync_and_async_resolvers_together(schema):
    result = await execute(schema, "{ ping asyncName }")
    assert result.errors == []
    assert result.data == {"ping": "pong", "asyncName": "async!"}


async def test_operation_selection_by_name(schema):
    document = """
    query A { ping }
    query B { asyncName }
    """
    result = await execute(schema, document, operation_name="B")
    assert result.data == {"asyncName": "async!"}


async def test_must_provide_operation_name_when_ambiguous(schema):
    document = "query A { ping } query B { ping }"
    result = await execute(schema, document)
    assert result.data is None
    assert any("operation name" in e.message for e in result.errors)


async def test_parse_failure_returns_errors_and_no_data(schema):
    result = await execute(schema, "{ user(id: }")
    assert result.executed is False
    assert result.errors
    assert "Syntax Error" in result.errors[0].message


async def test_validation_failure_returns_errors_and_no_data(schema):
    result = await execute(schema, "{ nope }")
    assert result.executed is False
    assert any("nope" in e.message for e in result.errors)


async def test_skip_directive_omits_field(schema):
    result = await execute(schema, "{ ping asyncName @skip(if: true) }")
    assert result.data == {"ping": "pong"}


async def test_include_directive_via_variable(schema):
    result = await execute(
        schema,
        "query($show: Boolean!) { ping asyncName @include(if: $show) }",
        variable_values={"show": False},
    )
    assert result.data == {"ping": "pong"}


async def test_argument_coercion_via_variable(schema):
    received = {}

    def resolve_echo(value):
        received["value"] = value
        return value

    query = ObjectType(
        "Query",
        fields={
            "echo": Field(
                Int, args={"value": Argument(NonNull(Int))}, resolver=resolve_echo
            )
        },
    )
    s = Schema(query)
    result = await execute(
        s, "query($v: Int!) { echo(value: $v) }", variable_values={"v": 5}
    )
    assert received["value"] == 5
    assert result.data == {"echo": 5}


async def test_resolver_error_on_nullable_field_nulls_only_that_field():
    def boom():
        raise RuntimeError("kaboom")

    query = ObjectType(
        "Query",
        fields={
            "ok": Field(String, resolver=lambda: "fine"),
            "bad": Field(String, resolver=boom),
        },
    )
    result = await execute(Schema(query), "{ ok bad }")

    assert result.data == {"ok": "fine", "bad": None}
    assert len(result.errors) == 1
    assert "kaboom" in result.errors[0].message
    assert result.errors[0].path == ["bad"]


async def test_null_propagates_through_non_null_field():
    def boom():
        raise RuntimeError("nope")

    obj = ObjectType(
        "Thing",
        fields={"value": Field(NonNull(String), resolver=boom)},
    )
    # `thing` is nullable; its non-null child errors, so `thing` becomes null
    # and the error is reported at the child's path.
    query = ObjectType(
        "Query",
        fields={"thing": Field(obj, resolver=lambda: object())},
    )
    result = await execute(Schema(query), "{ thing { value } }")

    assert result.data == {"thing": None}
    assert len(result.errors) == 1
    assert result.errors[0].path == ["thing", "value"]


async def test_genuine_null_in_non_null_field_is_reported():
    query = ObjectType(
        "Query",
        fields={"required": Field(NonNull(String), resolver=lambda: None)},
    )
    result = await execute(Schema(query), "{ required }")

    assert result.data is None
    assert any("Cannot return null" in e.message for e in result.errors)


async def test_list_field_resolves_each_item():
    query = ObjectType(
        "Query",
        fields={
            "nums": Field(
                ListType(NonNull(Int)), resolver=lambda: [1, 2, 3]
            )
        },
    )
    result = await execute(Schema(query), "{ nums }")
    assert result.data == {"nums": [1, 2, 3]}


# -- error extensions ---------------------------------------------------------


async def test_error_extensions_are_surfaced():
    def boom():
        raise GraphQLError("nope", extensions={"code": "FORBIDDEN"})

    query = ObjectType("Query", fields={"x": Field(String, resolver=boom)})
    result = await execute(Schema(query), "{ x }")

    formatted = result.errors[0].formatted()
    assert formatted["message"] == "nope"
    assert formatted["extensions"] == {"code": "FORBIDDEN"}


async def test_error_without_extensions_omits_key():
    def boom():
        raise GraphQLError("nope")

    query = ObjectType("Query", fields={"x": Field(String, resolver=boom)})
    result = await execute(Schema(query), "{ x }")

    assert "extensions" not in result.errors[0].formatted()


# -- error masking ------------------------------------------------------------


async def test_unexpected_error_masked_when_enabled():
    def boom():
        raise RuntimeError("secret db dsn leaked")

    query = ObjectType("Query", fields={"x": Field(String, resolver=boom)})
    result = await execute(Schema(query), "{ x }", mask_errors=True)

    error = result.errors[0]
    assert error.message == "Unexpected error."
    # The original exception is preserved internally for logging.
    assert isinstance(error.original_error, RuntimeError)
    assert "secret db dsn" in str(error.original_error)


async def test_custom_mask_message():
    def boom():
        raise RuntimeError("boom")

    query = ObjectType("Query", fields={"x": Field(String, resolver=boom)})
    result = await execute(
        Schema(query), "{ x }", mask_errors=True, mask_message="Server error"
    )
    assert result.errors[0].message == "Server error"


async def test_unexpected_error_not_masked_by_default():
    def boom():
        raise RuntimeError("raw message")

    query = ObjectType("Query", fields={"x": Field(String, resolver=boom)})
    result = await execute(Schema(query), "{ x }")
    assert "raw message" in result.errors[0].message


async def test_explicit_graphql_error_not_masked():
    def boom():
        raise GraphQLError("client-facing reason")

    query = ObjectType("Query", fields={"x": Field(String, resolver=boom)})
    result = await execute(Schema(query), "{ x }", mask_errors=True)
    # Explicit GraphQLError passes through regardless of the masking policy.
    assert result.errors[0].message == "client-facing reason"
