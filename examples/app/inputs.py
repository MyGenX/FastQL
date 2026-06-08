"""Input objects.

``@Input`` types are the typed payloads of arguments. Field types come from the
annotations; defaults come from ``Field(default=...)`` or a plain ``= value``. Required
fields (no default) must be declared before optional ones.

* ``CreatePostInput`` — the payload for the ``createPost`` mutation.
* ``PostFilter`` — optional filters for the ``posts`` query (note the custom
  ``DateTime`` scalar used as *input* in ``published_since``).
"""

from __future__ import annotations

from fastql import Field, Input

from examples.app.enums import PostStatus
from examples.app.scalars import DateTime


@Input
class CreatePostInput:
    title: str
    body: str
    status: PostStatus = Field(default=PostStatus.DRAFT)


@Input
class PostFilter:
    status: PostStatus | None = None
    published_since: DateTime | None = None


__all__ = ["CreatePostInput", "PostFilter"]
