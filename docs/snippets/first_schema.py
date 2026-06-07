import asyncio

from fastql import Arg, Field, Query, SchemaConfig, Type, build_schema, execute


@Type(description="A product available in the catalog.")
class Product:
    sku: str
    display_name: str = Field(name="name", description="Customer-facing name.")


@Query(name="Query")
class CatalogQuery:
    @Field(description="Look up one product by SKU.")
    def product(self, sku: str = Arg(description="Stable product identifier.")) -> Product:
        return Product(sku=sku, display_name="Mechanical keyboard")


schema = build_schema(query=CatalogQuery, config=SchemaConfig(auto_camel_case=True))


if __name__ == "__main__":
    result = asyncio.run(
        execute(schema, '{ product(sku: "kbd-1") { sku name } }')
    )
    assert result.errors == []
    assert result.data == {
        "product": {"sku": "kbd-1", "name": "Mechanical keyboard"}
    }
