"""FastQL showcase application — a small blog/community API.

This is the reusable, framework-agnostic schema that the per-framework projects under
``examples/projects`` all mount, demonstrating that the same code-first schema integrates
into FastAPI, Starlette, Flask, Django, or raw ASGI with only a few lines of glue.

Every part of the authoring surface is exercised here — see ``examples/app/README.md`` for
the file-by-file map. Canonical entry points:

* ``examples.app:schema`` — the assembled :class:`~fastql.Schema`.
* ``examples.app:make_context`` — a zero-argument context factory (dev server / CLI).

Run the standalone demo with ``python -m examples.app.demo``.
"""

from __future__ import annotations

from examples.app.context import AppContext, make_context
from examples.app.data import STORE, reseed
from examples.app.loaders import BATCH_CALLS
from examples.app.schema import schema
from examples.app.types import Comment, Post, SearchResult, User

__all__ = [
    "schema",
    "make_context",
    "AppContext",
    "STORE",
    "reseed",
    "BATCH_CALLS",
    "User",
    "Post",
    "Comment",
    "SearchResult",
]
