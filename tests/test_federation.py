"""Apollo Federation v2 directives, SDL, and entity execution."""

import pytest

from fastql import Field, ListType, NonNull, Query, Type, execute
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.federation import (
    FEDERATION_IMPORTS,
    Schema,
    clear_reference_resolvers,
    external,
    inaccessible,
    key,
    override,
    print_federated_schema,
    provides,
    reference_resolver,
    requires,
    shareable,
    tag,
)


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()
    clear_reference_resolvers()


def test_federation_directives_render_with_link_imports():
    @Type(directives=[key("id"), shareable(), inaccessible(), tag("catalog")])
    class Product:
        id: int
        sku: str = Field(directives=[external()])

        @Field(directives=[requires("sku"), override("inventory")])
        def name(self) -> str:
            return "Chair"

        @Field(directives=[provides("id")])
        def related(self) -> "Product":
            return self

    @Query
    class Q:
        @Field
        def product(self) -> Product:
            return Product(id=1, sku="chair")

    sdl = print_federated_schema(Schema(query=Q))

    assert sdl.startswith("extend schema @link(")
    assert all(f'"{name}"' in sdl for name in FEDERATION_IMPORTS)
    assert (
        'type Product @key(fields: "id") @shareable @inaccessible '
        '@tag(name: "catalog") {'
    ) in sdl
    assert "sku: String! @external" in sdl
    assert 'name: String! @requires(fields: "sku") @override(from: "inventory")' in sdl
    assert 'related: Product! @provides(fields: "id")' in sdl
    assert "_Service" not in sdl
    assert "_Entity" not in sdl
    assert "_service" not in sdl
    assert "_entities" not in sdl


async def test_service_returns_gateway_facing_sdl():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    result = await execute(Schema(query=Q), "{ _service { sdl } }")

    assert result.errors == []
    service_sdl = result.data["_service"]["sdl"]
    assert "extend schema @link" in service_sdl
    assert "type Query" in service_sdl
    assert "ping: String!" in service_sdl
    assert "_service" not in service_sdl


async def test_entities_resolve_in_representation_order():
    calls = []

    @Type(directives=[key("id")])
    class Product:
        id: int
        name: str

    @Type(directives=[key("username")])
    class User:
        username: str

    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @reference_resolver(Product)
    def resolve_product(id: int, info) -> Product:
        calls.append(("Product", id, info.field_name))
        return Product(id=id, name=f"Product {id}")

    @reference_resolver(User)
    async def resolve_user(representation: dict) -> User:
        calls.append(("User", representation["username"], "_entities"))
        return User(username=representation["username"])

    schema = Schema(query=Q, types=[Product, User])
    entities_field = schema.query.fields["_entities"]
    assert isinstance(entities_field.type, NonNull)
    assert isinstance(entities_field.type.of_type, ListType)
    assert entities_field.type.of_type.of_type.name == "_Entity"
    representations = entities_field.args["representations"].type
    assert isinstance(representations, NonNull)
    assert isinstance(representations.of_type, ListType)
    assert isinstance(representations.of_type.of_type, NonNull)
    assert representations.of_type.of_type.of_type.name == "_Any"

    result = await execute(
        schema,
        """
        query Entities($representations: [_Any!]!) {
          _entities(representations: $representations) {
            __typename
            ... on Product { id name }
            ... on User { username }
          }
        }
        """,
        variable_values={
            "representations": [
                {"__typename": "User", "username": "ada"},
                {"__typename": "Product", "id": 7},
                {"__typename": "Missing", "id": 1},
            ]
        },
    )

    assert result.errors == []
    assert result.data == {
        "_entities": [
            {"__typename": "User", "username": "ada"},
            {"__typename": "Product", "id": 7, "name": "Product 7"},
            None,
        ]
    }
    assert calls == [
        ("User", "ada", "_entities"),
        ("Product", 7, "_entities"),
    ]


async def test_entities_accept_inline_any_representations():
    @Type(directives=[key("id", resolvable=False)])
    class Product:
        id: int

    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    reference_resolver(Product, lambda id: Product(id=id))
    result = await execute(
        Schema(query=Q, types=[Product]),
        """
        {
          _entities(representations: [{__typename: Product, id: 3}]) {
            ... on Product { id }
          }
        }
        """,
    )

    assert result.errors == []
    assert result.data == {"_entities": [{"id": 3}]}
    assert '@key(fields: "id", resolvable: false)' in print_federated_schema(
        Schema(query=Q, types=[Product])
    )
