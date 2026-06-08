"""DataLoader batch functions — the N+1 cure.

Each function takes a list of keys and returns results *positionally aligned* to
those keys. Resolvers reach them through :func:`fastql.get_loader`, which creates one
loader per request (stored on the context) and coalesces every ``.load(key)`` made in
the same tick into a single batch call.

``BATCH_CALLS`` records each invocation of :func:`load_posts_by_author` so a demo or
test can prove that ``users { posts { ... } }`` triggers exactly one batched load
(``[[1, 2]]``) instead of one query per user.
"""

from __future__ import annotations

from examples.app.data import STORE
from examples.app.types import Comment, Post, User

#: Records the key lists passed to ``load_posts_by_author`` (for the no-N+1 demo).
BATCH_CALLS: list[list[int]] = []


async def load_user(ids: list[int]) -> list[User | None]:
    return [STORE.users.get(i) for i in ids]


async def load_posts_by_author(user_ids: list[int]) -> list[list[Post]]:
    BATCH_CALLS.append(list(user_ids))
    return [
        [STORE.posts[pid] for pid in STORE.post_ids_by_author.get(uid, [])]
        for uid in user_ids
    ]


async def load_comments_by_post(post_ids: list[int]) -> list[list[Comment]]:
    return [
        [STORE.comments[cid] for cid in STORE.comment_ids_by_post.get(pid, [])]
        for pid in post_ids
    ]


__all__ = ["BATCH_CALLS", "load_user", "load_posts_by_author", "load_comments_by_post"]
