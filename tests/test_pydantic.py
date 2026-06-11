"""Optional Pydantic integration: type/input generation and validation.

Generation/validation tests require Pydantic; the import-guard test runs without
it and asserts the core stays importable and that the integration names its
extra when Pydantic is missing.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from fastql import Field, Query, Schema, execute, print_schema
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.types.wrappers import ListType, NonNull

ROOT = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def _named(type_ref):
    while isinstance(type_ref, (NonNull, ListType)):
        type_ref = type_ref.of_type
    return type_ref


async def test_object_type_generated_from_model():
    pytest.importorskip("pydantic")
    from pydantic import BaseModel

    from fastql.pydantic import pydantic_type

    class UserModel(BaseModel):
        id: int
        name: str
        nickname: str | None = None

    pydantic_type(UserModel, name="User")

    @Query
    class Q:
        @Field
        def user(self) -> UserModel:
            return UserModel(id=1, name="Ada")

    schema = Schema(query=Q)

    user = schema.type_map["User"]
    assert isinstance(user.fields["id"].type, NonNull)
    assert _named(user.fields["id"].type).name == "Int"
    assert _named(user.fields["name"].type).name == "String"
    # Optional model field maps to a nullable GraphQL field.
    assert not isinstance(user.fields["nickname"].type, NonNull)

    result = await execute(schema, "{ user { id name nickname } } ")
    assert result.errors == []
    assert result.data == {"user": {"id": 1, "name": "Ada", "nickname": None}}


async def test_input_type_carries_optionality_and_defaults():
    pytest.importorskip("pydantic")
    from pydantic import BaseModel

    from fastql.pydantic import pydantic_input

    class FilterInput(BaseModel):
        term: str
        limit: int = 10
        tags: list[str] | None = None

    pydantic_input(FilterInput, name="Filter")

    @Query
    class Q:
        @Field
        def search(self, filter: FilterInput) -> int:
            assert isinstance(filter, FilterInput)
            return filter.limit

    schema = Schema(query=Q)

    filter_type = schema.type_map["Filter"]
    assert isinstance(filter_type.fields["term"].type, NonNull)
    assert not isinstance(filter_type.fields["tags"].type, NonNull)
    assert filter_type.fields["limit"].default_value == 10

    sdl = print_schema(schema)
    assert "limit: Int! = 10" in sdl

    # Default applies when the field is omitted; the model is constructed.
    result = await execute(schema, '{ search(filter: { term: "hi" }) }')
    assert result.errors == []
    assert result.data == {"search": 10}


async def test_invalid_input_surfaces_validation_error():
    pytest.importorskip("pydantic")
    from pydantic import BaseModel, field_validator

    from fastql.pydantic import pydantic_input

    class SignUpInput(BaseModel):
        age: int

        @field_validator("age")
        @classmethod
        def must_be_adult(cls, value: int) -> int:
            if value < 18:
                raise ValueError("must be 18 or older")
            return value

    pydantic_input(SignUpInput, name="SignUp")

    @Query
    class Q:
        @Field
        def register(self, data: SignUpInput) -> bool:
            return True

    schema = Schema(query=Q)

    # Inline literal path.
    result = await execute(schema, "{ register(data: { age: 5 }) }")
    assert result.errors, "expected a validation error"
    assert "must be 18 or older" in result.errors[0].message

    # Variable path surfaces the same error rather than crashing.
    result = await execute(
        schema,
        "query ($d: SignUp!) { register(data: $d) }",
        variable_values={"d": {"age": 5}},
    )
    assert result.errors
    assert "must be 18 or older" in result.errors[0].message

    # A valid value passes validation and reaches the resolver.
    ok = await execute(schema, "{ register(data: { age: 21 }) }")
    assert ok.errors == []
    assert ok.data == {"register": True}


def test_core_imports_without_pydantic_and_integration_names_extra():
    code = """
import builtins
import asyncio
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'pydantic' or name.startswith('pydantic'):
        raise ImportError('blocked for test')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked

# Core stays importable and operational without Pydantic.
import fastql

@fastql.Query
class Q:
    @fastql.Field
    def ping(self) -> str:
        return 'pong'

result = asyncio.run(fastql.execute(fastql.Schema(query=Q), '{ ping }'))
assert result.data == {'ping': 'pong'}

# The integration module imports, but using it without Pydantic names the extra.
from fastql.pydantic import pydantic_type
try:
    pydantic_type(object)
except ImportError as error:
    assert 'mygenx-fastql[pydantic]' in str(error)
else:
    raise AssertionError('missing optional dependency was accepted')
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
