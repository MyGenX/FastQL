"""Per-request context.

:class:`AppContext` is the value resolvers receive as ``ctx``/``Context``. It carries
the signed-in user, which permissions and the ``me`` query read. A real adapter builds
one of these per request from the incoming HTTP request (see the per-framework projects
under ``examples/projects``); :func:`make_context` is the zero-argument factory used by
the dev server and CLI.
"""

from __future__ import annotations

from fastql import Context

from examples.app.data import STORE
from examples.app.types import User


class AppContext(Context):
    """Request context carrying the authenticated user (if any)."""

    def __init__(self, current_user: User | None = None) -> None:
        self.current_user = current_user


def make_context() -> AppContext:
    """Default context for the dev server / CLI — signed in as the admin (Ada)."""
    return AppContext(current_user=STORE.users[1])


__all__ = ["AppContext", "make_context"]
