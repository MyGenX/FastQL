"""SDL printer tests for the schema-endpoints capability."""

from fastql.sdl import print_schema
from fastql.types import (
    Argument,
    EnumType,
    Field,
    ID,
    NonNull,
    ObjectType,
    String,
)
from fastql.types.schema import Schema


def test_print_schema_renders_types_fields_and_args():
    user = ObjectType("User", fields={"id": Field(NonNull(ID)), "name": Field(String)})
    query = ObjectType(
        "Query",
        fields={"user": Field(user, args={"id": Argument(NonNull(ID))})},
    )
    sdl = print_schema(Schema(query))

    assert "type Query {" in sdl
    assert "type User {" in sdl
    assert "id: ID!" in sdl
    assert "user(id: ID!): User" in sdl
    # Built-in scalars are not redeclared.
    assert "scalar ID" not in sdl


def test_print_schema_renders_deprecation():
    query = ObjectType(
        "Query",
        fields={"legacy": Field(String, deprecation_reason="use modern")},
    )
    sdl = print_schema(Schema(query))
    assert 'legacy: String @deprecated(reason: "use modern")' in sdl


def test_print_schema_renders_enum():
    color = EnumType.from_names("Color", ["RED", "BLUE"])
    query = ObjectType("Query", fields={"color": Field(color)})
    sdl = print_schema(Schema(query))
    assert "enum Color {" in sdl
    assert "  RED" in sdl
    assert "  BLUE" in sdl
