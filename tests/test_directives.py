"""Author-defined directives: definition, location enforcement, SDL, coercion."""

import pytest

from fastql import (
    AppliedDirective,
    Directive,
    Field,
    Query,
    Schema,
    Type,
    execute,
    print_schema,
)
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.schema_builder import SchemaBuildError


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def test_directive_definition_registered_and_introspectable():
    @Directive(locations=["FIELD_DEFINITION", "OBJECT"], description="tag things")
    class tag:
        name: str

    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    schema = Schema(query=Q)
    assert "tag" in schema.directives
    definition = schema.directives["tag"]
    assert definition.locations == ["FIELD_DEFINITION", "OBJECT"]
    assert "name" in definition.args


async def test_directive_appears_in_introspection():
    @Directive(locations=["FIELD_DEFINITION"])
    class tag:
        name: str

    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    result = await execute(
        Schema(query=Q), "{ __schema { directives { name locations } } }"
    )
    names = {d["name"] for d in result.data["__schema"]["directives"]}
    assert "tag" in names


def test_applied_directive_rendered_in_sdl():
    @Directive(locations=["FIELD_DEFINITION", "OBJECT"])
    class tag:
        name: str

    @Type(directives=[AppliedDirective("tag", {"name": "obj"})])
    class Widget:
        id: int

        @Field(directives=[AppliedDirective("tag", {"name": "fieldlevel"})])
        def label(self) -> str:
            return "w"

    @Query
    class Q:
        @Field
        def widget(self) -> Widget:
            return Widget(id=1)

    sdl = print_schema(Schema(query=Q))
    assert 'type Widget @tag(name: "obj") {' in sdl
    assert 'label: String! @tag(name: "fieldlevel")' in sdl


def test_invalid_location_is_rejected():
    @Directive(locations=["FIELD_DEFINITION"])
    class fieldonly:
        pass

    @Type(directives=[AppliedDirective("fieldonly")])
    class A:
        id: int

    @Query
    class Q:
        @Field
        def a(self) -> A:
            return A(id=1)

    with pytest.raises(SchemaBuildError, match="not allowed on OBJECT"):
        Schema(query=Q)


def test_directive_argument_coercion_failure_is_rejected():
    @Directive(locations=["FIELD_DEFINITION"])
    class limit:
        count: int

    @Query
    class Q:
        @Field(directives=[AppliedDirective("limit", {"count": "not-an-int"})])
        def b(self) -> int:
            return 1

    with pytest.raises(SchemaBuildError):
        Schema(query=Q)


def test_unknown_directive_argument_is_rejected():
    @Directive(locations=["FIELD_DEFINITION"])
    class limit:
        count: int

    @Query
    class Q:
        @Field(directives=[AppliedDirective("limit", {"nope": 1})])
        def b(self) -> int:
            return 1

    with pytest.raises(SchemaBuildError, match="Unknown argument"):
        Schema(query=Q)
