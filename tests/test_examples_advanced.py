"""End-to-end coverage for the independent Phase 2 cookbook schemas."""

from fastql import GraphQLTestClient, print_schema
from fastql.relay import offset_to_cursor, to_global_id

from examples.advanced.generics import schema as generics_schema
from examples.advanced.relay import register_nodes, schema as relay_schema
from examples.advanced.schema_metadata import schema as metadata_schema


async def test_generic_recipe_synthesizes_and_executes_distinct_pages():
    assert "UserPage" in generics_schema.type_map
    assert "PostPage" in generics_schema.type_map

    result = await GraphQLTestClient(generics_schema).execute(
        "{ users { total items { name } } posts { total items { title } } }"
    )

    assert result.errors == []
    assert result.data == {
        "users": {"total": 2, "items": [{"name": "Ada"}, {"name": "Grace"}]},
        "posts": {
            "total": 2,
            "items": [
                {"title": "Analytical Engine"},
                {"title": "The First Compiler"},
            ],
        },
    }


async def test_relay_recipe_resolves_global_node():
    register_nodes()
    global_id = to_global_id("RelayUser", 2)

    result = await GraphQLTestClient(relay_schema).execute(
        '{ node(id: "%s") { __typename ... on RelayUser { id name } } }'
        % global_id
    )

    assert result.errors == []
    assert result.data == {
        "node": {"__typename": "RelayUser", "id": global_id, "name": "Grace"}
    }


async def test_relay_recipe_paginates_forward_and_backward():
    client = GraphQLTestClient(relay_schema)
    after = offset_to_cursor(0)
    forward = await client.execute(
        '{ users(first: 2, after: "%s") {'
        " edges { node { name } cursor }"
        " pageInfo { hasNextPage hasPreviousPage startCursor endCursor } } }"
        % after
    )
    assert [edge["node"]["name"] for edge in forward.data["users"]["edges"]] == [
        "Grace",
        "Linus",
    ]
    assert forward.data["users"]["pageInfo"]["hasNextPage"] is True

    before = offset_to_cursor(3)
    backward = await client.execute(
        '{ users(last: 2, before: "%s") {'
        " edges { node { name } }"
        " pageInfo { hasNextPage hasPreviousPage startCursor endCursor } } }"
        % before
    )
    assert [edge["node"]["name"] for edge in backward.data["users"]["edges"]] == [
        "Grace",
        "Linus",
    ]
    assert backward.data["users"]["pageInfo"]["hasPreviousPage"] is True


async def test_metadata_recipe_exposes_directive_and_enum_metadata():
    client = GraphQLTestClient(metadata_schema)
    result = await client.execute(
        "{ __schema { directives { name locations } } "
        '__type(name: "Availability") { enumValues(includeDeprecated: true) {'
        " name description isDeprecated deprecationReason } } "
        "product { availability label } }"
    )

    directives = {item["name"]: item for item in result.data["__schema"]["directives"]}
    assert directives["tag"]["locations"] == ["OBJECT", "FIELD_DEFINITION"]
    values = {
        item["name"]: item
        for item in result.data["__type"]["enumValues"]
    }
    assert values["ON_HOLD"]["description"] == "Temporarily unavailable."
    assert values["LEGACY"]["deprecationReason"] == "Use ACTIVE."
    assert result.data["product"] == {
        "availability": "ON_HOLD",
        "label": "internal-001: product 1",
    }


async def test_metadata_recipe_hides_private_and_renders_schema_annotations():
    result = await GraphQLTestClient(metadata_schema).execute(
        '{ __type(name: "Product") { fields { name } } }'
    )
    names = {field["name"] for field in result.data["__type"]["fields"]}
    assert "internalCode" not in names
    assert {"id", "externalSku", "availability", "label"} <= names

    sdl = print_schema(metadata_schema)
    assert 'type Product @tag(name: "catalog") {' in sdl
    assert 'label: String! @tag(name: "display")' in sdl
    assert "externalSku: String! @external" in sdl
    assert "internalCode" not in sdl
    assert 'LEGACY @deprecated(reason: "Use ACTIVE.")' in sdl
