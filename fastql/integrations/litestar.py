"""Litestar-native FastQL router integration.

Litestar is ASGI-native, so the adapter mounts the shared :class:`GraphQLASGI`
application (HTTP + ``graphql-transport-ws``) at the configured path.
"""

from __future__ import annotations

from typing import Any

try:
    from litestar import Router
    from litestar.handlers import asgi
    from litestar.types import Receive, Scope, Send
except ImportError as error:  # pragma: no cover - exercised in isolated import tests
    raise ImportError(
        "The Litestar adapter requires 'mygenx-fastql[litestar]'."
    ) from error

from fastql.integrations.asgi import GraphQLASGI


def create_litestar_router(
    schema: Any,
    *,
    path: str = "/graphql",
    **options: Any,
) -> "Router":
    """Create a Litestar ``Router`` mounting the FastQL ASGI application."""

    application = GraphQLASGI(schema, path=path, **options)
    mount_path = path.rstrip("/")

    @asgi(path, is_mount=True, copy_scope=False)
    async def graphql(scope: "Scope", receive: "Receive", send: "Send") -> None:
        # Litestar strips the mount prefix; restore the full path so the shared
        # ASGI app can route the main, schema, and GraphiQL endpoints.
        inner = scope.get("path", "/")
        full = mount_path if inner in ("", "/") else mount_path + inner
        await application({**scope, "path": full, "root_path": ""}, receive, send)

    return Router(path="/", route_handlers=[graphql])


__all__ = ["create_litestar_router"]
