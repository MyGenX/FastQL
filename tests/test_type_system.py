"""Type-system IR tests covering the type-system OpenSpec scenarios."""

import pytest

from fastql.language import ast
from fastql.types import (
    Argument,
    Boolean,
    Field,
    ID,
    InputField,
    InputObjectType,
    Int,
    ListType,
    NonNull,
    ObjectType,
    ScalarCoercionError,
    Schema,
    String,
)


def test_object_type_exposes_fields_and_arguments_by_name():
    user = ObjectType(
        "User",
        fields={
            "name": Field(String),
            "friend": Field(
                String,
                args={"id": Argument(NonNull(ID), description="Friend ID")},
                description="Look up a friend by ID.",
            ),
        },
    )

    assert user.name == "User"
    assert set(user.fields) == {"name", "friend"}
    assert user.fields["name"].type is String
    assert user.fields["friend"].args["id"].type == NonNull(ID)
    assert user.fields["friend"].args["id"].description == "Friend ID"


def test_wrapping_types_preserve_nesting_order():
    field_type = NonNull(ListType(NonNull(String)))

    assert isinstance(field_type, NonNull)
    assert isinstance(field_type.of_type, ListType)
    assert isinstance(field_type.of_type.of_type, NonNull)
    assert field_type.of_type.of_type.of_type is String


def test_non_null_rejects_nested_non_null():
    with pytest.raises(TypeError, match="NonNull cannot wrap another NonNull"):
        NonNull(NonNull(String))


def test_int_scalar_serialization_and_coercion():
    assert Int.serialize(42) == 42
    assert Int.parse_value(42) == 42
    assert Int.parse_literal(ast.IntValueNode("42")) == 42

    with pytest.raises(ScalarCoercionError, match="Invalid Int value"):
        Int.parse_value("abc")
    with pytest.raises(ScalarCoercionError, match="Invalid Int value"):
        Int.serialize(True)


def test_id_accepts_string_and_integer_values():
    assert ID.serialize("abc") == "abc"
    assert ID.serialize(123) == "123"
    assert ID.parse_value("abc") == "abc"
    assert ID.parse_value(123) == "123"
    assert ID.parse_literal(ast.StringValueNode("abc")) == "abc"
    assert ID.parse_literal(ast.IntValueNode("123")) == "123"

    with pytest.raises(ScalarCoercionError, match="Invalid ID value"):
        ID.parse_value(True)


def test_builtin_scalar_coercion_rejects_wrong_literal_kinds():
    assert Boolean.parse_literal(ast.BooleanValueNode(True)) is True
    assert String.parse_literal(ast.StringValueNode("ok")) == "ok"

    with pytest.raises(ScalarCoercionError, match="Invalid Boolean value"):
        Boolean.parse_literal(ast.StringValueNode("true"))
    with pytest.raises(ScalarCoercionError, match="Invalid String value"):
        String.parse_literal(ast.IntValueNode("1"))


def test_schema_type_map_contains_reachable_types_from_query_root():
    profile_input = InputObjectType(
        "ProfileInput",
        fields={"nickname": InputField(String)},
    )
    profile = ObjectType("Profile", fields={"nickname": Field(String)})
    user = ObjectType(
        "User",
        fields={
            "id": Field(NonNull(ID)),
            "profile": Field(profile, args={"input": Argument(profile_input)}),
        },
    )
    query = ObjectType("Query", fields={"user": Field(user, args={"id": Argument(ID)})})

    schema = Schema(query)

    assert schema.query is query
    assert schema.type_map["Query"] is query
    assert schema.type_map["User"] is user
    assert schema.type_map["Profile"] is profile
    assert schema.type_map["ProfileInput"] is profile_input
    assert schema.type_map["ID"] is ID
    assert schema.type_map["String"] is String
    assert "include" in schema.directives
    assert "skip" in schema.directives
    assert "deprecated" in schema.directives


def test_schema_accepts_explicit_unreachable_types():
    orphan = ObjectType("Orphan", fields={"name": Field(String)})
    query = ObjectType("Query", fields={"ok": Field(Boolean)})

    schema = Schema(query, types=[orphan])

    assert schema.type_map["Orphan"] is orphan
