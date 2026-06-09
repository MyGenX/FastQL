"""Private (schema-excluded) and external (federation) field markers."""

import pytest

from fastql import Field, Query, Schema, Type, execute, print_schema
from fastql.context import default_dependencies
from fastql.decorators import default_registry


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def _schema_with_widget():
    @Type
    class Widget:
        id: int
        secret: str = Field(private=True)

        @Field
        def reveal(self) -> str:
            return f"secret={self.secret}"

    @Query
    class Q:
        @Field
        def widget(self) -> Widget:
            return Widget(id=1, secret="hidden")

    return Schema(query=Q), Widget


def test_private_field_absent_from_schema_and_sdl():
    schema, _ = _schema_with_widget()
    assert "secret" not in schema.type_map["Widget"].fields
    assert "secret" not in print_schema(schema)


async def test_private_field_absent_from_introspection():
    schema, _ = _schema_with_widget()
    result = await execute(
        schema, '{ __type(name: "Widget") { fields { name } } }'
    )
    names = {f["name"] for f in result.data["__type"]["fields"]}
    assert "secret" not in names
    assert {"id", "reveal"} <= names


async def test_private_attribute_remains_usable_in_python():
    schema, Widget = _schema_with_widget()
    # The attribute exists on the instance...
    assert Widget(id=2, secret="s").secret == "s"
    # ...and a resolver can read it even though it is not a schema field.
    result = await execute(schema, "{ widget { reveal } }")
    assert result.data == {"widget": {"reveal": "secret=hidden"}}


def test_external_field_declared_with_external_directive():
    @Type
    class User:
        id: int
        handle: str = Field(external=True)

    @Query
    class Q:
        @Field
        def user(self) -> User:
            return User(id=1, handle="ada")

    schema = Schema(query=Q)
    # External fields stay in the schema (declared) and render @external in SDL.
    assert "handle" in schema.type_map["User"].fields
    assert schema.type_map["User"].fields["handle"].external is True
    assert "handle: String! @external" in print_schema(schema)
