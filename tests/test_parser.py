"""Parser tests covering the language-parsing 'Parse a document into an AST' scenarios."""

import pytest

from fastql.errors import GraphQLSyntaxError
from fastql.language import ast
from fastql.language.parser import parse
from fastql.language.printer import print_ast


def test_named_query_with_variables():
    doc = parse("query GetUser($id: ID!) { user(id: $id) { name } }")
    assert isinstance(doc, ast.DocumentNode)
    assert len(doc.definitions) == 1

    op = doc.definitions[0]
    assert isinstance(op, ast.OperationDefinitionNode)
    assert op.operation == "query"
    assert op.name.value == "GetUser"

    # One variable definition: $id of non-null type ID.
    assert len(op.variable_definitions) == 1
    var_def = op.variable_definitions[0]
    assert var_def.variable.name.value == "id"
    assert isinstance(var_def.type, ast.NonNullTypeNode)
    assert isinstance(var_def.type.type, ast.NamedTypeNode)
    assert var_def.type.type.name.value == "ID"

    # Selection set contains the `user` field with an `id: $id` argument.
    selections = op.selection_set.selections
    assert len(selections) == 1
    user_field = selections[0]
    assert isinstance(user_field, ast.FieldNode)
    assert user_field.name.value == "user"
    assert user_field.arguments[0].name.value == "id"
    assert isinstance(user_field.arguments[0].value, ast.VariableNode)


def test_query_shorthand():
    doc = parse("{ a b }")
    op = doc.definitions[0]
    assert op.operation == "query"
    assert op.name is None
    assert [s.name.value for s in op.selection_set.selections] == ["a", "b"]


def test_field_alias():
    doc = parse("{ shortName: name }")
    field = doc.definitions[0].selection_set.selections[0]
    assert field.alias.value == "shortName"
    assert field.name.value == "name"


def test_fragments_spread_and_inline():
    query = """
    query {
      hero {
        ...heroFields
        ... on Droid {
          primaryFunction
        }
      }
    }
    fragment heroFields on Character { name }
    """
    doc = parse(query)
    op = doc.definitions[0]
    hero = op.selection_set.selections[0]
    spread, inline = hero.selection_set.selections
    assert isinstance(spread, ast.FragmentSpreadNode)
    assert spread.name.value == "heroFields"
    assert isinstance(inline, ast.InlineFragmentNode)
    assert inline.type_condition.name.value == "Droid"

    frag = doc.definitions[1]
    assert isinstance(frag, ast.FragmentDefinitionNode)
    assert frag.type_condition.name.value == "Character"


def test_directives_and_values():
    doc = parse('{ a(x: 1, y: "s", z: [true, null], o: {k: 1}) @skip(if: false) }')
    field = doc.definitions[0].selection_set.selections[0]
    arg_names = [a.name.value for a in field.arguments]
    assert arg_names == ["x", "y", "z", "o"]
    assert field.directives[0].name.value == "skip"


def test_node_locations_are_recorded():
    doc = parse("{ name }")
    field = doc.definitions[0].selection_set.selections[0]
    assert field.loc is not None
    assert field.loc.start < field.loc.end


def test_syntax_error_reports_location():
    with pytest.raises(GraphQLSyntaxError) as exc:
        parse("{ user(id: 1 ")  # missing closing paren / brace
    err = exc.value
    assert "Syntax Error" in err.message
    assert err.locations


def test_mutation_and_subscription_operations():
    assert parse("mutation { like }").definitions[0].operation == "mutation"
    assert parse("subscription { onX }").definitions[0].operation == "subscription"


def test_printer_round_trips_structure():
    doc = parse("query GetUser($id: ID!) { user(id: $id) { name } }")
    printed = print_ast(doc)
    # Re-parsing the printed output yields an equivalent structure.
    reparsed = parse(printed)
    op = reparsed.definitions[0]
    assert op.name.value == "GetUser"
    assert op.selection_set.selections[0].name.value == "user"
