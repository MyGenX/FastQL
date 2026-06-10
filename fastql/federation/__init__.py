"""Apollo Federation v2 schema support."""

from fastql.federation.directives import (
    FEDERATION_IMPORTS,
    FEDERATION_SPEC_URL,
    external,
    federation_directives,
    inaccessible,
    key,
    override,
    provides,
    requires,
    shareable,
    tag,
)
from fastql.federation.sdl import print_federated_schema
from fastql.federation.schema import (
    Schema,
    clear_reference_resolvers,
    reference_resolver,
    register_reference,
)

__all__ = [
    "FEDERATION_IMPORTS",
    "FEDERATION_SPEC_URL",
    "Schema",
    "clear_reference_resolvers",
    "external",
    "federation_directives",
    "inaccessible",
    "key",
    "override",
    "print_federated_schema",
    "provides",
    "requires",
    "reference_resolver",
    "register_reference",
    "shareable",
    "tag",
]
