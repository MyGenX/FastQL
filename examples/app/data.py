"""In-memory data store and seed data.

This stands in for a database. A real application would replace :class:`Store`
with repositories backed by SQL/HTTP, but the resolver and DataLoader code above it
would not change — which is the point of keeping persistence behind a small seam.

There is a single module-level :data:`STORE`. :func:`reseed` repopulates it *in
place* (so every module that imported ``STORE`` keeps a valid reference); tests call
it between cases to stay isolated.
"""

from __future__ import annotations

from datetime import datetime, timezone

from examples.app.enums import PostStatus, Role
from examples.app.types import Comment, Post, User


def _ts(day: int) -> datetime:
    return datetime(2024, 1, day, 12, 0, tzinfo=timezone.utc)


class Store:
    """Mutable in-memory graph of users, posts, and comments."""

    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.posts: dict[int, Post] = {}
        self.comments: dict[int, Comment] = {}
        # Relationship indexes, kept off the objects so the public types stay clean.
        self.post_ids_by_author: dict[int, list[int]] = {}
        self.author_id_by_post: dict[int, int] = {}
        self.comment_ids_by_post: dict[int, list[int]] = {}
        self.author_id_by_comment: dict[int, int] = {}
        self._next_id = 1000

    # -- writes (used by mutations) -------------------------------------------

    def add_post(self, *, title: str, body: str, status: PostStatus, author: User) -> Post:
        post = Post(
            id=self._allocate(),
            title=title,
            body=body,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        self.posts[post.id] = post
        self.author_id_by_post[post.id] = author.id
        self.post_ids_by_author.setdefault(author.id, []).append(post.id)
        self.comment_ids_by_post.setdefault(post.id, [])
        return post

    def add_comment(self, *, post_id: int, body: str, author: User) -> Comment:
        comment = Comment(id=self._allocate(), body=body)
        self.comments[comment.id] = comment
        self.author_id_by_comment[comment.id] = author.id
        self.comment_ids_by_post.setdefault(post_id, []).append(comment.id)
        return comment

    def set_status(self, post_id: int, status: PostStatus) -> Post | None:
        post = self.posts.get(post_id)
        if post is not None:
            post.status = status
        return post

    # -- reads -----------------------------------------------------------------

    def find_node(self, node_id: int):
        return self.users.get(node_id) or self.posts.get(node_id) or self.comments.get(node_id)

    def _allocate(self) -> int:
        self._next_id += 1
        return self._next_id


#: The single in-memory store. Repopulate with :func:`reseed`.
STORE = Store()


def reseed() -> Store:
    """Reset :data:`STORE` to its seed state, in place."""
    s = STORE
    s.users = {
        1: User(id=1, name="Ada Lovelace", role=Role.ADMIN, sort_key="01"),
        2: User(id=2, name="Grace Hopper", role=Role.MEMBER, sort_key="02"),
    }
    s.posts = {
        10: Post(10, "On the Analytical Engine", "First algorithm.", PostStatus.PUBLISHED, _ts(1)),
        11: Post(11, "Notes on Note G", "Working notes.", PostStatus.DRAFT, _ts(2)),
        20: Post(20, "The First Compiler", "A-0 system.", PostStatus.PUBLISHED, _ts(3)),
    }
    s.comments = {
        100: Comment(100, "Groundbreaking."),
        101: Comment(101, "Inspiring work."),
    }
    s.author_id_by_post = {10: 1, 11: 1, 20: 2}
    s.post_ids_by_author = {1: [10, 11], 2: [20]}
    s.comment_ids_by_post = {10: [100], 11: [], 20: [101]}
    s.author_id_by_comment = {100: 2, 101: 1}
    s._next_id = 1000
    return s


reseed()


def author_id_for_post(post_id: int) -> int:
    return STORE.author_id_by_post[post_id]


def author_id_for_comment(comment_id: int) -> int:
    return STORE.author_id_by_comment[comment_id]


__all__ = ["Store", "STORE", "reseed", "author_id_for_post", "author_id_for_comment"]
