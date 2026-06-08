"""Shared context-building logic reused by every framework project.

A real app authenticates the incoming request and builds a per-request context. To keep
the examples self-contained, "authentication" here is just an ``X-User-Id`` header naming
a seeded user. Each framework project extracts that header in its own way and hands the
value here, so the actual context/authorization logic lives in exactly one place.

It also writes a response header through :class:`~fastql.integrations.http.ResponseControl`
to show how context-aware code can influence the HTTP response.
"""

from __future__ import annotations

from typing import Any

from examples.app import STORE, AppContext


def build_context(http_context: Any, user_id_header: str | None) -> AppContext:
    """Resolve the ``X-User-Id`` header to a seeded user and build an ``AppContext``."""
    user = None
    if user_id_header:
        try:
            user = STORE.users.get(int(user_id_header))
        except (TypeError, ValueError):
            user = None
    # Surface who we authenticated as on the response (demonstrates response control).
    http_context.response.set_header("X-FastQL-User", user.name if user else "anonymous")
    return AppContext(current_user=user)


__all__ = ["build_context"]
