"""Object types and a union.

* ``@Type`` classes (``User``, ``Post``, ``Comment``) get auto-generated
  constructors / ``repr`` / ``eq`` from their annotations.
* Each implements the ``Node`` ``@Interface`` via ``interfaces=[Node]``.
* Relationship fields (``User.posts``, ``Post.author`` …) resolve through
  per-request :class:`DataLoader` s so a nested query batches its lookups instead
  of fanning out into N+1 calls. The loader batch functions live in
  :mod:`examples.app.loaders` and are imported lazily inside resolvers to avoid an
  import cycle (``loaders`` → ``data`` → ``types``).
* ``@Union`` exposes a "could be either" result, used by the ``search`` query. The
  executor picks the concrete member from the returned object's type, so resolvers
  just return a ``User`` or a ``Post`` — no manual type tag required.
"""

from __future__ import annotations

from fastql import Field, Info, Type, Union, get_loader

from examples.app.enums import PostStatus, Role
from examples.app.interfaces import Node
from examples.app.scalars import DateTime


@Type(interfaces=[Node])
class User:
    id: int
    name: str
    role: Role = Field(default=Role.MEMBER)

    @Field
    def loud_name(self) -> str:
        return self.name.upper()

    @Field
    async def posts(self, info: Info) -> list["Post"]:
        from examples.app.loaders import load_posts_by_author

        return await get_loader(info, load_posts_by_author).load(self.id)


@Type(interfaces=[Node])
class Post:
    id: int
    title: str
    body: str
    status: PostStatus
    created_at: DateTime

    @Field
    async def author(self, info: Info) -> User:
        from examples.app.data import author_id_for_post
        from examples.app.loaders import load_user

        return await get_loader(info, load_user).load(author_id_for_post(self.id))

    @Field
    async def comments(self, info: Info) -> list["Comment"]:
        from examples.app.loaders import load_comments_by_post

        return await get_loader(info, load_comments_by_post).load(self.id)


@Type(interfaces=[Node])
class Comment:
    id: int
    body: str

    @Field
    async def author(self, info: Info) -> User:
        from examples.app.data import author_id_for_comment
        from examples.app.loaders import load_user

        return await get_loader(info, load_user).load(author_id_for_comment(self.id))


@Union(User, Post)
class SearchResult:
    """A search hit that is either a ``User`` or a ``Post``."""


__all__ = ["User", "Post", "Comment", "SearchResult"]
