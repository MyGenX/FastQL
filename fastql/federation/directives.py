"""Apollo Federation v2 directive metadata.

The helpers in this module return ordinary :class:`fastql.AppliedDirective`
instances, so federation annotations compose with the existing ``@Type`` and
``Field(directives=[...])`` authoring APIs.
"""

from __future__ import annotations

from fastql.types import AppliedDirective, Argument, Boolean, DirectiveDefinition
from fastql.types import NonNull, String

FEDERATION_SPEC_URL = "https://specs.apollo.dev/federation/v2.7"
FEDERATION_IMPORTS = (
    "@key",
    "@external",
    "@shareable",
    "@requires",
    "@provides",
    "@inaccessible",
    "@override",
    "@tag",
)


def key(fields: str, *, resolvable: bool = True) -> AppliedDirective:
    arguments: dict[str, object] = {"fields": fields}
    if not resolvable:
        arguments["resolvable"] = False
    return AppliedDirective("key", arguments)


def external() -> AppliedDirective:
    return AppliedDirective("external")


def shareable() -> AppliedDirective:
    return AppliedDirective("shareable")


def requires(fields: str) -> AppliedDirective:
    return AppliedDirective("requires", {"fields": fields})


def provides(fields: str) -> AppliedDirective:
    return AppliedDirective("provides", {"fields": fields})


def inaccessible() -> AppliedDirective:
    return AppliedDirective("inaccessible")


def override(from_: str, *, label: str | None = None) -> AppliedDirective:
    arguments = {"from": from_}
    if label is not None:
        arguments["label"] = label
    return AppliedDirective("override", arguments)


def tag(name: str) -> AppliedDirective:
    return AppliedDirective("tag", {"name": name})


def federation_directives() -> dict[str, DirectiveDefinition]:
    """Return definitions for the supported Federation v2 directives."""
    field_set = NonNull(String)
    name = NonNull(String)
    all_type_system_locations = [
        "FIELD_DEFINITION",
        "OBJECT",
        "INTERFACE",
        "UNION",
        "ARGUMENT_DEFINITION",
        "SCALAR",
        "ENUM",
        "ENUM_VALUE",
        "INPUT_OBJECT",
        "INPUT_FIELD_DEFINITION",
    ]
    return {
        "key": DirectiveDefinition(
            "key",
            locations=["OBJECT", "INTERFACE"],
            args={
                "fields": Argument(field_set),
                "resolvable": Argument(Boolean, default_value=True),
            },
            is_repeatable=True,
        ),
        "external": DirectiveDefinition(
            "external", locations=["OBJECT", "FIELD_DEFINITION"]
        ),
        "shareable": DirectiveDefinition(
            "shareable",
            locations=["OBJECT", "FIELD_DEFINITION"],
            is_repeatable=True,
        ),
        "requires": DirectiveDefinition(
            "requires",
            locations=["FIELD_DEFINITION"],
            args={"fields": Argument(field_set)},
        ),
        "provides": DirectiveDefinition(
            "provides",
            locations=["FIELD_DEFINITION"],
            args={"fields": Argument(field_set)},
        ),
        "inaccessible": DirectiveDefinition(
            "inaccessible", locations=all_type_system_locations
        ),
        "override": DirectiveDefinition(
            "override",
            locations=["FIELD_DEFINITION"],
            args={"from": Argument(name), "label": Argument(String)},
        ),
        "tag": DirectiveDefinition(
            "tag",
            locations=[*all_type_system_locations, "SCHEMA"],
            args={"name": Argument(name)},
            is_repeatable=True,
        ),
    }


__all__ = [
    "FEDERATION_IMPORTS",
    "FEDERATION_SPEC_URL",
    "external",
    "federation_directives",
    "inaccessible",
    "key",
    "override",
    "provides",
    "requires",
    "shareable",
    "tag",
]
