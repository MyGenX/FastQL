"""Decorator authoring-surface tests for schema-definition scenarios."""

from enum import Enum as PythonEnum

import pytest

from fastql.decorators import (
    Enum,
    Field,
    Input,
    Interface,
    Mutation,
    Query,
    Scalar,
    Subscription,
    Type,
    TypeReference,
    Union,
    default_registry,
    resolve_type_hint,
)
from fastql.types import (
    Boolean,
    EnumType,
    Float,
    ID,
    InputObjectType,
    Int,
    ListType,
    NonNull,
    ObjectType,
    ScalarType,
    String,
    UnionType,
)


@pytest.fixture(autouse=True)
def clear_registry():
    default_registry.clear()


def assert_non_null(type_, inner):
    assert isinstance(type_, NonNull)
    assert type_.of_type is inner


def test_type_decorator_registers_object_fields_from_annotations():
    @Type
    class User:
        id: int
        name: str

    gql_type = User.__fastql_type__

    assert isinstance(gql_type, ObjectType)
    assert gql_type.name == "User"
    assert_non_null(gql_type.fields["id"].type, Int)
    assert_non_null(gql_type.fields["name"].type, String)
    assert default_registry.types_by_python[User] is gql_type


def test_field_descriptor_overrides_description_deprecation_and_name():
    @Type
    class User:
        legacy: str = Field(name="oldName", deprecated="use modern", description="Old value")

    field = User.__fastql_type__.fields["oldName"]

    assert_non_null(field.type, String)
    assert field.description == "Old value"
    assert field.deprecation_reason == "use modern"


def test_field_method_decorator_registers_computed_field():
    @Type
    class User:
        first: str
        last: str

        @Field
        def full_name(self) -> str:
            return f"{self.first} {self.last}"

    field = User.__fastql_type__.fields["full_name"]

    assert_non_null(field.type, String)
    assert field.resolver is not None
    # The auto-generated constructor accepts the data fields directly.
    user = User("Ada", "Lovelace")
    assert field.resolver(user) == "Ada Lovelace"


def test_input_decorator_registers_input_fields():
    @Input
    class UserInput:
        name: str
        age: int | None

    gql_type = UserInput.__fastql_type__

    assert isinstance(gql_type, InputObjectType)
    assert_non_null(gql_type.fields["name"].type, String)
    assert gql_type.fields["age"].type is Int


def test_interface_implementation_lists_and_inherits_interface_fields():
    @Interface
    class Node:
        id: ID

    @Type(interfaces=[Node])
    class User:
        name: str

    gql_type = User.__fastql_type__

    assert gql_type.interfaces == [Node.__fastql_type__]
    assert "id" in gql_type.fields
    assert_non_null(gql_type.fields["id"].type, ID)
    assert_non_null(gql_type.fields["name"].type, String)


def test_type_hint_inference_for_optional_list_and_forward_ref():
    field_type = resolve_type_hint(list["User"] | None, module=__name__)

    assert isinstance(field_type, ListType)
    assert isinstance(field_type.of_type, NonNull)
    assert isinstance(field_type.of_type.of_type, TypeReference)
    assert field_type.of_type.of_type.name == "User"


def test_type_hint_inference_for_registered_type_and_scalars():
    @Type
    class User:
        id: ID

    assert_non_null(resolve_type_hint(User), User.__fastql_type__)
    assert_non_null(resolve_type_hint(bool), Boolean)
    assert_non_null(resolve_type_hint(float), Float)


def test_enum_decorator_registers_python_enum_members():
    @Enum
    class Color(PythonEnum):
        RED = "red"
        BLUE = "blue"

    gql_type = Color.__fastql_type__

    assert isinstance(gql_type, EnumType)
    assert set(gql_type.values) == {"RED", "BLUE"}
    assert gql_type.values["RED"].value == "red"


def test_union_decorator_registers_object_members():
    @Type
    class User:
        id: ID

    @Type
    class Organization:
        id: ID

    @Union(User, Organization)
    class SearchResult:
        pass

    gql_type = SearchResult.__fastql_type__

    assert isinstance(gql_type, UnionType)
    assert gql_type.types == [User.__fastql_type__, Organization.__fastql_type__]


def test_scalar_decorator_registers_custom_scalar_hooks():
    @Scalar
    class Date:
        @staticmethod
        def serialize(value):
            return str(value)

        @staticmethod
        def parse_value(value):
            return f"parsed:{value}"

        @staticmethod
        def parse_literal(value):
            return f"literal:{value.value}"

    gql_type = Date.__fastql_type__

    assert isinstance(gql_type, ScalarType)
    assert gql_type.serialize(123) == "123"
    assert gql_type.parse_value("x") == "parsed:x"


def test_operation_class_decorators_register_root_fields_and_arguments():
    @Type
    class User:
        id: ID

    @Query
    class Queries:
        @Field
        def user(self, id: ID, context: object) -> "User":
            return User()

    @Mutation
    class Mutations:
        @Field(name="renameUser")
        def rename(self, id: ID, name: str) -> bool:
            return True

    @Subscription
    class Subscriptions:
        @Field
        def user_events(self, id: ID) -> str:
            return "updated"

    query_def = default_registry.operations["query"]["user"]
    mutation_def = default_registry.operations["mutation"]["renameUser"]
    subscription_def = default_registry.operations["subscription"]["user_events"]

    assert query_def.field.resolver is Queries.__dict__["user"].resolver
    assert set(query_def.field.args) == {"id"}
    assert_non_null(query_def.field.args["id"].type, ID)
    assert isinstance(query_def.field.type.of_type, TypeReference)
    assert query_def.field.type.of_type.name == "User"
    assert set(mutation_def.field.args) == {"id", "name"}
    assert_non_null(mutation_def.field.type, Boolean)
    assert_non_null(subscription_def.field.type, String)
