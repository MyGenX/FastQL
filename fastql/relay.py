"""Relay Cursor Connections + global object identification.

Built on FastQL generics (see :mod:`fastql.schema_builder`), this module provides:

* the :class:`Node` interface and a global-ID codec (``base64("Type:id")``) with a
  type→resolver registry behind :func:`resolve_node` for a root ``node(id)`` query;
* generic :class:`Connection`, :class:`Edge`, and :class:`PageInfo` types;
* :func:`connection_from_list`, a cursor-slicing helper implementing the Relay
  forward/backward pagination algorithm.

This module deliberately avoids ``from __future__ import annotations`` so the generic
field annotations (``node: T``, ``edges: list[Edge[T]]``) stay live objects that the
type-hint resolver can introspect directly.
"""

import base64
import binascii
import inspect
from typing import Any, Callable, Generic, Sequence, TypeVar

from fastql.decorators import Field, Interface, Type
from fastql.types import ID

T = TypeVar("T")

_CURSOR_PREFIX = "cursor:"


# --- global object identification -------------------------------------------


def to_global_id(type_name: str, inner_id: Any) -> str:
    """Encode a ``(type_name, inner_id)`` pair into an opaque global ID."""
    return base64.b64encode(f"{type_name}:{inner_id}".encode("utf-8")).decode("ascii")


def from_global_id(global_id: str) -> tuple[str, str]:
    """Decode a global ID back into ``(type_name, inner_id)``.

    Returns ``("", "")`` for malformed input rather than raising.
    """
    try:
        decoded = base64.b64decode(global_id, validate=True).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return "", ""
    type_name, separator, inner_id = decoded.partition(":")
    if not separator:
        return "", ""
    return type_name, inner_id


@Interface
class Node:
    """An object with a globally unique ``id``."""

    id: ID


#: type name -> callable that fetches an object by its decoded inner id.
_node_resolvers: dict[str, Callable[..., Any]] = {}


def register_node(type_name: str, fetch: Callable[..., Any]) -> None:
    """Register ``fetch(inner_id[, info])`` to resolve ``type_name`` by inner id."""
    _node_resolvers[type_name] = fetch


def clear_node_registry() -> None:
    """Drop all registered node resolvers (useful for test isolation)."""
    _node_resolvers.clear()


def register_types() -> None:
    """Re-register the Relay types into the default registry.

    The Relay types register on import; call this to restore them after a
    ``default_registry.clear()`` (e.g. in test fixtures or multi-schema apps).
    """
    from fastql.decorators import default_registry

    for cls in (Node, PageInfo):
        default_registry.register_type(cls, cls.__fastql_type__)
    for cls in (Edge, Connection):
        default_registry.generic_templates[cls] = cls.__fastql_generic__


def resolve_node(global_id: str, info: Any = None) -> Any:
    """Decode ``global_id`` and dispatch to the registered resolver for its type.

    Wire this into a root field, e.g.::

        @Query
        class Query:
            @Field
            def node(self, id: ID, info: Info) -> "Node | None":
                return resolve_node(id, info)
    """
    type_name, inner_id = from_global_id(global_id)
    fetch = _node_resolvers.get(type_name)
    if fetch is None:
        return None
    if _accepts_info(fetch):
        return fetch(inner_id, info)
    return fetch(inner_id)


def _accepts_info(fetch: Callable[..., Any]) -> bool:
    try:
        parameters = inspect.signature(fetch).parameters
    except (TypeError, ValueError):
        return False
    positional = [
        p
        for p in parameters.values()
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional) >= 2 or any(
        p.kind == inspect.Parameter.VAR_POSITIONAL for p in parameters.values()
    )


# --- connection types -------------------------------------------------------


@Type
class PageInfo:
    """Relay pagination metadata for a page of edges."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None


@Type
class Edge(Generic[T]):
    """A single edge: a node plus its opaque cursor."""

    node: T
    cursor: str


@Type
class Connection(Generic[T]):
    """A page of edges over a list of ``T`` plus :class:`PageInfo`."""

    edges: list[Edge[T]]
    page_info: PageInfo


# --- cursor slicing ---------------------------------------------------------


def offset_to_cursor(offset: int) -> str:
    """Encode a positional offset into an opaque cursor."""
    return base64.b64encode(f"{_CURSOR_PREFIX}{offset}".encode("utf-8")).decode("ascii")


def cursor_to_offset(cursor: str) -> int | None:
    """Decode a cursor back into its offset, or ``None`` if malformed."""
    try:
        decoded = base64.b64decode(cursor, validate=True).decode("utf-8")
        return int(decoded[len(_CURSOR_PREFIX):])
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None


def _offset_with_default(cursor: str | None, default: int) -> int:
    if cursor is None:
        return default
    offset = cursor_to_offset(cursor)
    return default if offset is None else offset


def connection_from_list(
    data: Sequence[Any],
    *,
    first: int | None = None,
    after: str | None = None,
    last: int | None = None,
    before: str | None = None,
    edge_type: Callable[..., Any] = Edge,
    connection_type: Callable[..., Any] = Connection,
    page_info_type: Callable[..., Any] = PageInfo,
) -> Any:
    """Slice ``data`` per the Relay Cursor Connections algorithm.

    Honors ``first``/``after`` (forward) and ``last``/``before`` (backward), builds
    edges with positional cursors, and populates the page-info flags.
    """
    if first is not None and first < 0:
        raise ValueError("Argument 'first' must be a non-negative integer.")
    if last is not None and last < 0:
        raise ValueError("Argument 'last' must be a non-negative integer.")

    length = len(data)
    before_offset = _offset_with_default(before, length)
    after_offset = _offset_with_default(after, -1)

    start_offset = max(-1, after_offset) + 1
    end_offset = min(length, before_offset)
    if first is not None:
        end_offset = min(end_offset, start_offset + first)
    if last is not None:
        start_offset = max(start_offset, end_offset - last)

    start_offset = max(0, start_offset)
    end_offset = max(start_offset, min(end_offset, length))

    edges = [
        edge_type(node=data[offset], cursor=offset_to_cursor(offset))
        for offset in range(start_offset, end_offset)
    ]

    lower_bound = after_offset + 1 if after is not None else 0
    upper_bound = before_offset if before is not None else length
    page_info = page_info_type(
        has_previous_page=last is not None and start_offset > lower_bound,
        has_next_page=first is not None and end_offset < upper_bound,
        start_cursor=edges[0].cursor if edges else None,
        end_cursor=edges[-1].cursor if edges else None,
    )
    return connection_type(edges=edges, page_info=page_info)


__all__ = [
    "Node",
    "PageInfo",
    "Edge",
    "Connection",
    "to_global_id",
    "from_global_id",
    "register_node",
    "clear_node_registry",
    "register_types",
    "resolve_node",
    "connection_from_list",
    "offset_to_cursor",
    "cursor_to_offset",
]
