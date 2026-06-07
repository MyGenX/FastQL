"""Query-validation tests covering the query-validation OpenSpec scenarios."""

import pytest

from fastql.language.parser import parse
from fastql.types import (
    Argument,
    Field,
    ID,
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
