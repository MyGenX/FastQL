"""Federated SDL rendering for Apollo Federation v2 subgraphs."""

from __future__ import annotations

import copy
import json
from typing import Any

from fastql.federation.directives import FEDERATION_IMPORTS, FEDERATION_SPEC_URL
from fastql.sdl import print_schema

_SUPPORT_TYPES = {"_Any", "_Entity", "_FieldSet", "_Service"}
_SUPPORT_QUERY_FIELDS = {"_entities", "_service"}


def print_federated_schema(schema: Any) -> str:
    """Return gateway-facing Federation v2 SDL for ``schema``.

    Runtime support types and root fields are implementation details of the
    subgraph protocol, so they are omitted from the service SDL.
    """
    view = copy.copy(schema)
    query = copy.copy(schema.query)
    query.fields = {
        name: field
        for name, field in schema.query.fields.items()
        if name not in _SUPPORT_QUERY_FIELDS and not name.startswith("__")
    }
    view.query = query
    view.type_map = {
        name: (query if type_ is schema.query else type_)
        for name, type_ in schema.type_map.items()
        if name not in _SUPPORT_TYPES
    }
    imports = ", ".join(json.dumps(name) for name in FEDERATION_IMPORTS)
    link = (
        "extend schema "
        f"@link(url: {json.dumps(FEDERATION_SPEC_URL)}, import: [{imports}])"
    )
    body = print_schema(view).rstrip()
    return link + (f"\n\n{body}\n" if body else "\n")


__all__ = ["print_federated_schema"]
