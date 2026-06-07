"""Tests for auto-generated constructors and operation container classes."""

import pytest

from fastql.decorators import Field, Mutation, Query, Type, default_registry
from fastql.execution import execute
from fastql.schema_builder import build_schema
from fastql.types import ID, Int, NonNull, String


@pytest.fixture(autouse=True)
def clear_registry():
    default_registry.clear()


# --- auto-generated constructors --------------------------------------------


def test_autogen_constructor_positional_and_keyword():
    @Type
    class User:
        id: int
        name: str

    assert User(1, "Ada").id == 1
    assert User(id=2, name="Grace").name == "Grace"


def test_autogen_constructor_honors_defaults():
    @Type
    class User:
        name: str
        active: bool = True

    assert User("Ada").active is True
    assert User("Ada", active=False).active is False


def test_autogen_repr_and_eq():
    @Type
    class Point:
        x: int
        y: int

    assert repr(Point(1, 2)) == "Point(x=1, y=2)"
    assert Point(1, 2) == Point(1, 2)
    assert Point(1, 2) != Point(1, 3)


def test_user_defined_init_is_preserved():
    @Type
    class User:
        id: int
        name: str

        def __init__(self, id: int, name: str = "anon") -> None:
            self.id = id
            self.name = name.upper()

    assert User(1).name == "ANON"
    assert User(1, "ada").name == "ADA"


def test_field_resolver_attribute_is_computed_not_constructor_arg():
    def upper_name(parent) -> str:
        return parent.name.upper()

    @Type
    class User:
        name: str
        shout: str = Field(resolver=upper_name)

    gql = User.__fastql_type__
    assert "shout" in gql.fields
    assert gql.fields["shout"].resolver is upper_name
    # `shout` is computed, so it is not a constructor parameter.
    user = User("ada")
    assert user.name == "ada"


# --- operation container classes --------------------------------------------


async def test_query_class_with_multiple_field_methods():
    @Type
    class User:
        id: int
        name: str

    @Query
    class Queries:
        @Field
        def user(self, id: int) -> "User":
            return User(id, f"User {id}")

        @Field
        def ping(self) -> str:
            return "pong"

    schema = build_schema()
    assert set(schema.query.fields) >= {"user", "ping"}
    # `self` is bound to the container instance, not exposed as an argument.
    assert set(schema.query.fields["user"].args) == {"id"}

    result = await execute(schema, "{ user(id: 7) { id name } ping }")
    assert result.errors == []
    assert result.data == {"user": {"id": 7, "name": "User 7"}, "ping": "pong"}


async def test_multiple_query_classes_merge():
    @Type
    class User:
        id: int

    @Query
    class UserQueries:
        @Field
        def user(self, id: int) -> "User":
            return User(id)

    @Query
    class HealthQueries:
        @Field
        def ping(self) -> str:
            return "pong"

    schema = build_schema()
    assert {"user", "ping"} <= set(schema.query.fields)


def test_duplicate_field_name_across_classes_raises():
    @Query
    class A:
        @Field
        def ping(self) -> str:
            return "a"

    with pytest.raises(ValueError, match="Duplicate query field 'ping'"):

        @Query
        class B:
            @Field
            def ping(self) -> str:
                return "b"


async def test_mutation_class_form():
    @Type
    class User:
        id: int
        name: str

    @Query
    class Queries:
        @Field
        def ping(self) -> str:
            return "pong"

    @Mutation
    class Mutations:
        @Field
        def create_user(self, name: str) -> "User":
            return User(1, name)

    schema = build_schema()
    assert "createUser" in schema.mutation.fields

    result = await execute(schema, 'mutation { createUser(name: "Ada") { name } }')
    assert result.data == {"createUser": {"name": "Ada"}}


async def test_field_resolver_attribute_on_query_class():
    @Type
    class User:
        id: int

    def all_users() -> "list[User]":
        return [User(1), User(2)]

    @Query
    class Queries:
        users: "list[User]" = Field(resolver=all_users)

    schema = build_schema()
    result = await execute(schema, "{ users { id } }")
    assert result.data == {"users": [{"id": 1}, {"id": 2}]}


def test_standalone_query_function_is_rejected():
    with pytest.raises(TypeError, match="can only decorate a class"):

        @Query
        def user(id: int) -> int:
            return id
