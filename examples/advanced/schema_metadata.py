"""Custom directives, field visibility, and per-member enum metadata."""

from __future__ import annotations

from enum import Enum as PythonEnum

from fastql import (
    AppliedDirective,
    Directive,
    Enum,
    Field,
    Schema,
    Type,
    TypeRegistry,
    enum_value,
)


@Directive(
    locations=["OBJECT", "FIELD_DEFINITION"],
    description="Classifies schema elements for documentation tooling.",
)
class tag:
    name: str


@Enum
class Availability(PythonEnum):
    ACTIVE = enum_value("active", description="Available for new orders.")
    LEGACY = enum_value(
        "legacy",
        description="Kept for existing clients.",
        deprecation_reason="Use ACTIVE.",
    )
    PAUSED = enum_value(
        "paused", name="ON_HOLD", description="Temporarily unavailable."
    )


@Type(directives=[AppliedDirective("tag", {"name": "catalog"})])
class Product:
    id: int
    internal_code: str = Field(private=True)
    external_sku: str = Field(external=True)
    availability: Availability

    @Field(directives=[AppliedDirective("tag", {"name": "display"})])
    def label(self) -> str:
        return f"{self.internal_code}: product {self.id}"


PRODUCT = Product(
    id=1,
    internal_code="internal-001",
    external_sku="partner-001",
    availability=Availability.PAUSED,
)


@Type(name="Query")
class Queries:
    @Field
    def product(self) -> Product:
        return PRODUCT


registry = TypeRegistry()
for type_ in (Availability, Product, Queries):
    registry.register_type(type_, type_.__fastql_type__)
registry.register_directive(tag, tag.__fastql_directive__)

schema = Schema(query=Queries, registry=registry)

__all__ = ["Availability", "Product", "Queries", "schema", "tag"]
