"""Context / dependency-injection tests for the context-injection scenarios."""

import pytest

from fastql.context import (
    Context,
    ResolveInfo,
    default_dependencies,
    register_dependency,
)
from fastql.execution import execute
from fastql.types import Argument, Field, Int, NonNull, ObjectType, String
from fastql.types.schema import Schema


@pytest.fixture(autouse=True)
def clear_dependencies():
    default_dependencies.clear()


class AppContext(Context):
    def __init__(self, user):
        self.user = user


class CurrentUser:
    def __init__(self, name):
        self.name = name


async def test_argument_and_context_injected_together():
    captured = {}

    async def resolve(id, ctx: Context):
        captured["id"] = id
        captured["ctx"] = ctx
        return f"{ctx.user}:{id}"

    query = ObjectType(
        "Query",
        fields={
            "thing": Field(
                String, args={"id": Argument(NonNull(Int))}, resolver=resolve
            )
        },
    )
    ctx = AppContext(user="ada")
    result = await execute(
        Schema(query), '{ thing(id: 7) }', context=ctx
    )

    assert captured["id"] == 7
    assert captured["ctx"] is ctx
    assert result.data == {"thing": "ada:7"}


async def test_info_injection():
    captured = {}

    def resolve(info: ResolveInfo):
        captured["info"] = info
        return info.field_name

    query = ObjectType("Query", fields={"whoami": Field(String, resolver=resolve)})
    result = await execute(Schema(query), "{ whoami }")

    info = captured["info"]
    assert isinstance(info, ResolveInfo)
    assert info.field_name == "whoami"
    assert info.path == ["whoami"]
    assert result.data == {"whoami": "whoami"}


async def test_context_typed_by_any_parameter_name():
    # The parameter is named `environment`, not `context`/`ctx`; type drives it.
    def resolve(environment: AppContext):
        return environment.user

    query = ObjectType("Query", fields={"me": Field(String, resolver=resolve)})
    result = await execute(Schema(query), "{ me }", context=AppContext(user="grace"))

    assert result.data == {"me": "grace"}


async def test_unrequested_context_is_not_passed():
    def resolve():
        return "ok"

    query = ObjectType("Query", fields={"ping": Field(String, resolver=resolve)})
    result = await execute(Schema(query), "{ ping }", context=AppContext(user="x"))

    assert result.errors == []
    assert result.data == {"ping": "ok"}


async def test_registered_dependency_resolved_from_context():
    register_dependency(CurrentUser, lambda ctx: CurrentUser(ctx.user))

    def resolve(current: CurrentUser):
        return current.name

    query = ObjectType("Query", fields={"name": Field(String, resolver=resolve)})
    result = await execute(Schema(query), "{ name }", context=AppContext(user="lin"))

    assert result.data == {"name": "lin"}


async def test_context_typed_param_is_not_a_graphql_argument():
    # When using the @Query decorator, a Context-typed parameter must not become
    # a GraphQL argument.
    from fastql.decorators import Field as DecoratorField
    from fastql.decorators import Query, Type, default_registry

    default_registry.clear()

    @Type
    class User:
        name: str

    @Query
    class Queries:
        @DecoratorField
        def user(self, id: int, ctx: Context) -> "User":
            return User()

    definition = default_registry.operations["query"]["user"]
    assert set(definition.field.args) == {"id"}
