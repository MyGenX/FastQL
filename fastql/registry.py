"""Top-level type registry facade used by schema building.

Decorators (`@Type`, `@Query`, …) collect their definitions into a single
:class:`~fastql.decorators.registry.DecoratorRegistry`. This module exposes that
collector under the canonical name :class:`TypeRegistry` and re-exports the
process-wide :data:`default_registry` that the decorators populate and that
:func:`fastql.schema_builder.build_schema` reads by default.

Forward/circular references are *not* resolved here: decorators store unresolved
references as :class:`~fastql.decorators.annotations.TypeReference` thunks inside
the type IR, and the schema builder resolves them at build time.
"""

from __future__ import annotations

from fastql.decorators.registry import (
    DecoratorRegistry,
    OperationDefinition,
    default_registry,
)

# Canonical name for the registry that the schema builder and public API use.
TypeRegistry = DecoratorRegistry

__all__ = [
    "TypeRegistry",
    "DecoratorRegistry",
    "OperationDefinition",
    "default_registry",
]
