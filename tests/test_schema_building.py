"""Schema-building tests covering the schema-building OpenSpec scenarios."""

import pytest

from fastql.decorators import Query, Type, default_registry
from fastql.schema_builder import SchemaBuildError, build_schema
from fastql.types import (
    Boolean,
    Field,
    ID,
    InterfaceType,
    NonNull,
    ObjectType,
    String,
)


@pytest.fixture(autouse=True)
def clear_registry():
    default_registry.clear()


def test_build_from_query_root_collects_reachable_types():
    @Type
    class User:
        id: int
        name: str

    @Type
    class Query:
        user: User

    schema = build_schema(query=Query)

    assert schema.query.name == "Query"
    assert schema.type_map["User"] is not User.__fastql_type__
    # The forward reference on the query field now points at the resolved type.
    user_field = schema.query.fields["user"]
    assert user_field.type.of_type is schema.type_map["User"]


def test_circular_references_are_resolved():
    @Type
    class A:
        b: "B"

    @Type
    class B:
        a: "A"

    @Type
    class Query:
        a: A

    schema = build_schema(query=Query)

    a_ir = schema.type_map["A"]
    b_ir = schema.type_map["B"]
    # A.b -> B and B.a -> A, both unwrapped from their NonNull wrappers.
    assert a_ir.fields["b"].type.of_type is b_ir
    assert b_ir.fields["a"].type.of_type is a_ir
    assert a_ir is not A.__fastql_type__
    assert b_ir is not B.__fastql_type__


def test_explicitly_included_unreachable_type_is_in_type_map():
    @Type
    class Orphan:
        name: str

    @Type
    class Query:
        ok: bool

    schema = build_schema(query=Query, types=[Orphan])

    assert schema.type_map["Orphan"].name == "Orphan"
    assert schema.type_map["Orphan"] is not Orphan.__fastql_type__


def test_operations_assembled_from_registry_without_explicit_root():
    @Type
    class User:
        id: ID

    from fastql.decorators import Field as DecoratorField

    @Query
    class QueryRoot:
        @DecoratorField
        def me(self) -> User:
            return User()

    schema = build_schema()

    assert schema.query.name == "Query"
    assert "me" in schema.query.fields
    assert schema.type_map["User"].name == "User"
    assert schema.type_map["User"] is not User.__fastql_type__


def test_unresolved_type_reference_names_type_and_field():
    @Type
    class Query:
        ghost: "Ghost"  # never defined

    with pytest.raises(SchemaBuildError) as exc:
        build_schema(query=Query)

    message = str(exc.value)
    assert "Ghost" in message
    assert "Query.ghost" in message


def test_duplicate_type_name_raises():
    @Type
    class Query:
        ok: bool

    dup_a = ObjectType("Dup", fields={"x": Field(String)})
    dup_b = ObjectType("Dup", fields={"y": Field(String)})

    with pytest.raises(SchemaBuildError, match="Duplicate type name: Dup"):
        build_schema(query=Query, types=[dup_a, dup_b])


def test_interface_not_satisfied_raises():
    node = InterfaceType("Node", fields={"id": Field(NonNull(ID))})
    bad = ObjectType("Bad", fields={"name": Field(String)}, interfaces=[node])
    query = ObjectType("Query", fields={"bad": Field(bad)})

    with pytest.raises(SchemaBuildError) as exc:
        build_schema(query=query)

    message = str(exc.value)
    assert "id" in message and "Node" in message


def test_non_object_union_member_raises():
    from fastql.types import UnionType

    # A union whose member is a scalar (not an object type) is invalid.
    bad_union = UnionType("Bad", types=[String])
    query = ObjectType("Query", fields={"bad": Field(bad_union)})

    with pytest.raises(SchemaBuildError, match="member must be an object type"):
        build_schema(query=query)
