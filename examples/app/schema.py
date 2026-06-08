"""Assemble the showcase :class:`~fastql.Schema`.

Importing this module imports every type/operation module so their decorators register
before the schema is built with explicit roots. The two schema-wide extensions
(:class:`Timing`, :class:`ResolverCount`) attach observability to every operation.
"""

from __future__ import annotations

from fastql import Schema

# Importing these modules registers the types, inputs, scalars, enums, and providers.
from examples.app import inputs, providers, scalars  # noqa: F401
from examples.app.extensions import ResolverCount, Timing
from examples.app.mutations import Mutations
from examples.app.queries import Queries
from examples.app.subscriptions import Subscriptions

schema = Schema(
    query=Queries,
    mutation=Mutations,
    subscription=Subscriptions,
    extensions=[Timing, ResolverCount],
)

__all__ = ["schema"]
