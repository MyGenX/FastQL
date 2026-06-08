"""Field-level authorization via ``BasePermission``.

A permission class returns ``True``/``False`` from :meth:`has_permission`. When it
denies, the field resolves to ``null`` and its ``message`` is surfaced as a GraphQL
error — the resolver never runs. Attach them with
``@Field(permission_classes=[...])`` (see :mod:`examples.app.mutations`).
"""

from __future__ import annotations

from fastql import BasePermission

from examples.app.context import AppContext
from examples.app.enums import Role


class IsAuthenticated(BasePermission):
    message = "Authentication required."

    def has_permission(self, source, info, **kwargs) -> bool:
        ctx = info.context
        return isinstance(ctx, AppContext) and ctx.current_user is not None


class IsAdmin(BasePermission):
    message = "Admin role required."

    def has_permission(self, source, info, **kwargs) -> bool:
        ctx = info.context
        user = getattr(ctx, "current_user", None) if isinstance(ctx, AppContext) else None
        return user is not None and user.role == Role.ADMIN


__all__ = ["IsAuthenticated", "IsAdmin"]
