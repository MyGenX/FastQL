"""Unified Strawberry-style schema authoring scenarios."""

from typing import Annotated

import pytest

from fastql import (
    Arg,
    Argument,
    AppliedDirective,
    BasePermission,
    Context,
    Field,
    FieldExtension,
    Info,
    Input,
    Query,
    Schema,
    SchemaBuildError,
    SchemaConfig,
    Type,
    build_schema,
    execute,
    print_schema,
    register_dependency,
)
from fastql.context import default_dependencies
from fastql.decorators import default_registry


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


async def test_explicit_schema_camel_cases_fields_and_annotated_arguments():
    @Type
    class User:
        full_name: str

    @Query
    class Root:
        @Field
        def current_user(
            self, user_id: Annotated[int, Argument(name="id")]
        ) -> User:
            return User(f"User {user_id}")

    schema = Schema(query=Root)

    assert "currentUser" in schema.query.fields
    assert "fullName" in schema.type_map["User"].fields
    result = await execute(schema, "{ currentUser(id: 3) { fullName } }")
    assert result.errors == []
    assert result.data == {"currentUser": {"fullName": "User 3"}}


async def test_schema_can_disable_camel_case_and_arg_default_form_works():
    @Query
    class Root:
        @Field
        def echo_value(
            self, user_id: int = Arg(name="user_id", default=7)
        ) -> int:
            return user_id

    schema = Schema(query=Root, config=SchemaConfig(auto_camel_case=False))
    result = await execute(schema, "{ echo_value(user_id: 9) }")
    defaulted = await execute(schema, "{ echo_value }")

    assert result.errors == []
    assert result.data == {"echo_value": 9}
    assert defaulted.data == {"echo_value": 7}


async def test_input_is_constructed_as_python_value_with_default_factory():
    @Input
    class SearchInput:
        labels: list[str] = Field(default_factory=list)

    @Query
    class Root:
        @Field
        def label_count(self, search_input: SearchInput) -> int:
            assert isinstance(search_input, SearchInput)
            return len(search_input.labels)

    result = await execute(
        Schema(query=Root), "{ labelCount(searchInput: {}) }"
    )

    assert result.errors == []
    assert result.data == {"labelCount": 0}


async def test_root_instances_are_shared_per_operation_and_recreated():
    class AppContext(Context):
        pass

    @Query
    class Root:
        created = 0

        def __init__(self, context: AppContext):
            Root.created += 1
            self.number = Root.created
            self.context = context

        @Field
        def first(self) -> int:
            return self.number

        @Field
        def second(self) -> int:
            return self.number

    schema = Schema(query=Root)
    first = await execute(schema, "{ first second }", context=AppContext())
    second = await execute(schema, "{ first }", context=AppContext())

    assert first.data == {"first": 1, "second": 1}
    assert second.data == {"first": 2}


async def test_async_dependency_is_cached_for_one_execution():
    class Service:
        pass

    calls = 0

    async def provide_service(context):
        nonlocal calls
        calls += 1
        return Service()

    register_dependency(Service, provide_service)

    @Query
    class Root:
        @Field
        def left(self, service: Service) -> bool:
            return isinstance(service, Service)

        @Field
        def right(self, service: Service) -> bool:
            return isinstance(service, Service)

    result = await execute(Schema(query=Root), "{ left right }")

    assert result.data == {"left": True, "right": True}
    assert calls == 1


async def test_extensions_wrap_resolver_in_order():
    events = []

    class Trace(FieldExtension):
        def __init__(self, name):
            self.name = name

        async def resolve(self, next_, source, info, **kwargs):
            events.append(f"{self.name}:before")
            result = await next_(source, info, **kwargs)
            events.append(f"{self.name}:after")
            return result

    @Query
    class Root:
        @Field(extensions=[Trace("a"), Trace("b")])
        def value(self, info: Info) -> str:
            assert info.python_name == "value"
            events.append("resolver")
            return "ok"

    result = await execute(Schema(query=Root), "{ value }")

    assert result.data == {"value": "ok"}
    assert events == ["a:before", "b:before", "resolver", "b:after", "a:after"]


async def test_permission_denial_uses_graphql_error_propagation():
    class Denied(BasePermission):
        message = "Not allowed"

    @Query
    class Root:
        @Field(permission_classes=[Denied])
        def secret(self) -> str | None:
            raise AssertionError("resolver must not run")

    result = await execute(Schema(query=Root), "{ secret }")

    assert result.data == {"secret": None}
    assert [error.message for error in result.errors] == ["Not allowed"]


def test_applied_field_directive_is_preserved_in_sdl():
    @Query
    class Root:
        @Field(directives=[AppliedDirective("tag", {"name": "public"})])
        def status(self) -> str:
            return "ok"

    sdl = print_schema(Schema(query=Root))
    assert 'status: String! @tag(name: "public")' in sdl


def test_zero_argument_build_schema_merges_root_classes():
    @Query
    class Health:
        @Field
        def health_check(self) -> bool:
            return True

    @Query
    class Version:
        @Field
        def version(self) -> str:
            return "1"

    schema = build_schema(config=SchemaConfig())
    assert {"healthCheck", "version"} <= set(schema.query.fields)


async def test_unified_contract_spans_interface_and_all_root_kinds():
    from fastql import Interface, Mutation, Subscription

    @Interface
    class Node:
        external_id: int

    @Type(interfaces=[Node])
    class User:
        external_id: int
        display_name: str

    @Query
    class QueryRoot:
        @Field
        def current_user(self) -> User:
            return User(1, "Ada")

    @Mutation
    class MutationRoot:
        @Field
        def rename_user(self) -> User:
            return User(1, "Grace")

    @Subscription
    class SubscriptionRoot:
        @Field
        def user_updated(self) -> bool:
            return True

    schema = Schema(
        query=QueryRoot,
        mutation=MutationRoot,
        subscription=SubscriptionRoot,
    )

    assert "externalId" in schema.type_map["Node"].fields
    assert "displayName" in schema.type_map["User"].fields
    mutation = await execute(
        schema, "mutation { renameUser { externalId displayName } }"
    )
    subscription = await execute(schema, "subscription { userUpdated }")
    assert mutation.data == {
        "renameUser": {"externalId": 1, "displayName": "Grace"}
    }
    assert subscription.data == {"userUpdated": True}


def test_final_graphql_name_collision_is_rejected():
    @Query
    class Root:
        @Field
        def user_id(self) -> int:
            return 1

        @Field
        def userId(self) -> int:
            return 2

    with pytest.raises(SchemaBuildError, match="Duplicate field 'userId'"):
        Schema(query=Root)
