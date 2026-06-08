"""GraphQL enums.

``@Enum`` registers a standard ``enum.Enum`` subclass. A resolver may return either
the member (``Role.ADMIN``) or its value (``"ADMIN"``); on the wire it serializes to
the member *name*. Enums are also usable as input — e.g. ``PostFilter.status``.
"""

from __future__ import annotations

from enum import Enum as PythonEnum

from fastql import Enum


@Enum
class Role(PythonEnum):
    ADMIN = "admin"
    MEMBER = "member"


@Enum
class PostStatus(PythonEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def as_status(value: "PostStatus | str") -> PostStatus:
    """Normalize an enum member *or* its wire value to a ``PostStatus`` member.

    Inputs arriving over the wire coerce to the enum's *value* (e.g. ``"published"``),
    while Python-side defaults are members; this collapses both to a member so seeded
    and mutated data compare equal.
    """
    return value if isinstance(value, PostStatus) else PostStatus(value)


__all__ = ["Role", "PostStatus", "as_status"]
