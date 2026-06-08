"""Query-validation tests covering the query-validation OpenSpec scenarios."""

import pytest

from fastql.language.parser import parse
from fastql.types import (
    Argument,
    Field,
    ID,
    InputField,
    InputObjectType,
    NonNull,
    ObjectType,
    String,
)
from fastql.types.schema import Schema
from fastql.validation import validate


@pytest.fixture
def schema():
    user = ObjectType(
        "User",
        fields={
            "id": Field(NonNull(ID)),
            "name": Field(String, args={"upper": Argument(String)}),
        },
    )
    query = ObjectType(
        "Query",
        fields={"user": Field(user, args={"id": Argument(NonNull(ID))})},
    )
    return Schema(query)


def test_valid_operation_returns_no_errors(schema):
    doc = parse("query GetUser($id: ID!) { user(id: $id) { id name } }")
    assert validate(schema, doc) == []


def test_unknown_field_is_reported(schema):
    doc = parse("{ user(id: 1) { id ghost } }")
    errors = validate(schema, doc)
    assert len(errors) == 1
    assert "ghost" in errors[0].message
    assert "User" in errors[0].message
    assert errors[0].locations  # carries a source location


def test_unknown_argument_is_reported(schema):
    doc = parse("{ user(id: 1, limit: 5) { id } }")
    errors = validate(schema, doc)
    assert any("limit" in e.message for e in errors)


def test_undefined_variable_is_reported(schema):
    doc = parse("query { user(id: $missing) { id } }")
    errors = validate(schema, doc)
    assert any("$missing" in e.message and "not defined" in e.message for e in errors)


def test_defined_variable_is_accepted(schema):
    doc = parse("query GetUser($id: ID!) { user(id: $id) { id } }")
    assert validate(schema, doc) == []


def test_leaf_field_with_subselection_is_reported(schema):
    doc = parse("{ user(id: 1) { id { oops } } }")
    errors = validate(schema, doc)
    assert any("must not have a selection" in e.message for e in errors)


def test_composite_field_without_subselection_is_reported(schema):
    doc = parse("{ user(id: 1) }")
    errors = validate(schema, doc)
    assert any("must have a selection" in e.message for e in errors)


def test_invalid_scalar_argument_literal_is_reported(schema):
    # `name`'s `upper` argument is a String; passing an Int literal is invalid.
    doc = parse("{ user(id: 1) { name(upper: 5) } }")
    errors = validate(schema, doc)
    assert any("upper" in e.message for e in errors)


def test_unknown_fragment_spread_is_reported(schema):
    doc = parse("{ user(id: 1) { ...Missing } }")
    errors = validate(schema, doc)
    assert any("Missing" in e.message for e in errors)


def test_variable_used_inside_fragment_is_checked(schema):
    doc = parse(
        """
        query { user(id: 1) { ...F } }
        fragment F on User { name(upper: $who) }
        """
    )
    errors = validate(schema, doc)
    assert any("$who" in e.message for e in errors)


# -- validation-completeness rules --------------------------------------------


def test_no_fragment_cycles(schema):
    doc = parse(
        """
        query { user(id: 1) { ...A } }
        fragment A on User { id ...B }
        fragment B on User { name ...A }
        """
    )
    errors = validate(schema, doc)
    assert any("within itself" in e.message for e in errors)


def test_unknown_directive_is_reported(schema):
    doc = parse("{ user(id: 1) @foo { id } }")
    errors = validate(schema, doc)
    assert any("@foo" in e.message and "Unknown directive" in e.message for e in errors)


def test_directive_in_invalid_location_is_reported(schema):
    # @skip is valid on FIELD, not on an operation (QUERY).
    doc = parse("query @skip(if: true) { user(id: 1) { id } }")
    errors = validate(schema, doc)
    assert any("@skip" in e.message and "QUERY" in e.message for e in errors)


def test_impossible_inline_fragment_spread_is_reported(schema):
    # Parent type is User; an inline fragment on Query can never apply.
    doc = parse("{ user(id: 1) { id ... on Query { user(id: 2) { id } } } }")
    errors = validate(schema, doc)
    assert any("can never be of type" in e.message for e in errors)


def test_impossible_named_fragment_spread_is_reported(schema):
    doc = parse(
        """
        { user(id: 1) { ...OnQuery } }
        fragment OnQuery on Query { user(id: 1) { id } }
        """
    )
    errors = validate(schema, doc)
    assert any("can never be of type" in e.message for e in errors)


def test_lone_anonymous_operation_is_reported(schema):
    doc = parse(
        """
        { user(id: 1) { id } }
        query Named { user(id: 1) { id } }
        """
    )
    errors = validate(schema, doc)
    assert any("anonymous operation" in e.message for e in errors)


def test_duplicate_operation_names_are_reported(schema):
    doc = parse(
        """
        query Dup { user(id: 1) { id } }
        query Dup { user(id: 1) { id } }
        """
    )
    errors = validate(schema, doc)
    assert any("only one operation named 'Dup'" in e.message for e in errors)


def test_duplicate_variable_names_are_reported(schema):
    doc = parse("query Q($id: ID!, $id: ID!) { user(id: $id) { id } }")
    errors = validate(schema, doc)
    assert any("only one variable named '$id'" in e.message for e in errors)


def test_duplicate_argument_names_are_reported(schema):
    doc = parse("{ user(id: 1, id: 2) { id } }")
    errors = validate(schema, doc)
    assert any("only one argument named 'id'" in e.message for e in errors)


def test_duplicate_input_field_names_are_reported():
    flt = InputObjectType("Filter", fields={"q": InputField(String)})
    query = ObjectType(
        "Query", fields={"search": Field(String, args={"filter": Argument(flt)})}
    )
    input_schema = Schema(query)
    doc = parse('{ search(filter: { q: "a", q: "b" }) }')
    errors = validate(input_schema, doc)
    assert any("only one input field named 'q'" in e.message for e in errors)


def test_overlapping_fields_with_different_fields_conflict(schema):
    doc = parse("{ user(id: 1) { x: id x: name } }")
    errors = validate(schema, doc)
    assert any("conflict" in e.message and "different fields" in e.message for e in errors)


def test_overlapping_fields_with_differing_arguments_conflict(schema):
    doc = parse('{ user(id: 1) { name(upper: "A") name(upper: "B") } }')
    errors = validate(schema, doc)
    assert any(
        "conflict" in e.message and "differing arguments" in e.message
        for e in errors
    )


def test_compatible_overlapping_fields_are_allowed(schema):
    # Same field, same arguments under one alias merges cleanly.
    doc = parse('{ user(id: 1) { name(upper: "A") name(upper: "A") } }')
    assert validate(schema, doc) == []
