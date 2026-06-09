"""Generic type definitions and concrete synthesis at build time."""

from typing import Generic, TypeVar

import pytest

from fastql import Field, Query, Schema, Type, execute, print_schema
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.types.wrappers import ListType, NonNull

T = TypeVar("T")


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def _named(type_ref):
    while isinstance(type_ref, (NonNull, ListType)):
        type_ref = type_ref.of_type
    return type_ref


async def test_type_variable_field_resolves_from_concrete_parameter():
    @Type
    class User:
        id: int
        name: str

    @Type
    class Connection(Generic[T]):
        total: int
        items: list[T]

    @Query
    class Q:
        @Field
        def users(self) -> Connection[User]:
            return Connection(total=1, items=[User(1, "Ada")])

    schema = Schema(query=Q)

    # A concrete UserConnection is synthesized, with items typed [User!]!.
    connection = schema.type_map["UserConnection"]
    assert _named(connection.fields["items"].type) is schema.type_map["User"]

    result = await execute(schema, "{ users { total items { id name } } }")
    assert result.errors == []
    assert result.data == {"users": {"total": 1, "items": [{"id": 1, "name": "Ada"}]}}


def test_same_parametrization_yields_one_stable_type():
    @Type
    class User:
        id: int

    @Type
    class Box(Generic[T]):
        value: T

    @Query
    class Q:
        @Field
        def left(self) -> Box[User]:
            return Box(value=User(1))

        @Field
        def right(self) -> Box[User]:
            return Box(value=User(2))

    schema = Schema(query=Q)

    assert "UserBox" in schema.type_map
    left = _named(schema.query.fields["left"].type)
    right = _named(schema.query.fields["right"].type)
    assert left.name == "UserBox"
    assert left is right  # one synthesized type, shared by both references


def test_distinct_parametrizations_are_distinct_types():
    @Type
    class User:
        id: int

    @Type
    class Post:
        id: int

    @Type
    class Connection(Generic[T]):
        items: list[T]

    @Query
    class Q:
        @Field
        def users(self) -> Connection[User]:
            return Connection(items=[])

        @Field
        def posts(self) -> Connection[Post]:
            return Connection(items=[])

    schema = Schema(query=Q)

    assert "UserConnection" in schema.type_map
    assert "PostConnection" in schema.type_map
    assert schema.type_map["UserConnection"] is not schema.type_map["PostConnection"]


def test_custom_naming_override_replaces_derived_default():
    @Type
    class User:
        id: int

    @Type(name="Paginated{T}")
    class Page(Generic[T]):
        items: list[T]
        cursor: str

    @Query
    class Q:
        @Field
        def users(self) -> Page[User]:
            return Page(items=[], cursor="")

    schema = Schema(query=Q)

    assert "PaginatedUser" in schema.type_map
    assert "UserPage" not in schema.type_map  # the derived default is overridden
    sdl = print_schema(schema)
    assert "type PaginatedUser {" in sdl
    assert "items: [User!]!" in sdl
