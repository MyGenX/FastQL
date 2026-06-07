"""Union decorator."""

from __future__ import annotations

from typing import Callable

from fastql.decorators.registry import default_registry
from fastql.types import ObjectType, UnionType


def Union(
    *members: type | ObjectType,
    name: str | None = None,
    description: str | None = None,
    resolve_type=None,
) -> Callable[[type], type]:
    """Register a marker class as a GraphQL union over object types."""

    def decorate(target: type) -> type:
        type_ = UnionType(
            name or target.__name__,
            types=[_resolve_object(member) for member in members],
            description=description,
            resolve_type=resolve_type,
        )
        default_registry.register_type(target, type_)
        return target

    return decorate


def _resolve_object(member: type | ObjectType) -> ObjectType:
    if isinstance(member, ObjectType):
        return member
    type_ = getattr(member, "__fastql_type__", None)
    if isinstance(type_, ObjectType):
        return type_
    raise TypeError(f"{member!r} is not a registered FastQL object type")


__all__ = ["Union"]
