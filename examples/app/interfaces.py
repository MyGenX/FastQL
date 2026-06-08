"""A shared ``Node`` interface.

``@Interface`` declares fields that implementing ``@Type`` classes must also expose.
``User``, ``Post``, and ``Comment`` all carry an ``id`` and implement ``Node`` via
``@Type(interfaces=[Node])``, so a fragment ``... on Node { id }`` matches any of them.

The id is modelled as a plain ``int`` (GraphQL ``Int!``) to keep example output JSON
numeric; a real app would typically use the built-in ``ID`` scalar here.
"""

from __future__ import annotations

from fastql import Interface


@Interface
class Node:
    id: int


__all__ = ["Node"]
