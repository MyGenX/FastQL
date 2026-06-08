"""Root mutations.

Mutations write to the ``STORE`` and publish to the pub/sub so subscribers see the
change. Authorization is declarative: ``permission_classes`` run before the resolver and
short-circuit to an error if denied. ``createPost`` also carries a ``FieldExtension``
(``AuditLog``) to show resolver-wrapping middleware at the field level.
"""

from __future__ import annotations

from fastql import Context, Field, FieldExtension, Mutation

from examples.app.context import AppContext
from examples.app.data import STORE
from examples.app.enums import PostStatus, as_status
from examples.app.inputs import CreatePostInput
from examples.app.permissions import IsAdmin, IsAuthenticated
from examples.app.pubsub import pubsub
from examples.app.types import Comment, Post


class AuditLog(FieldExtension):
    """A field-level extension that records each mutation call."""

    #: Appended to on every wrapped resolution: ``(field_name, source_repr)``.
    entries: list[tuple[str, str]] = []

    async def resolve(self, next_, source, info, **kwargs):
        result = next_(source, info, **kwargs)
        if hasattr(result, "__await__"):
            result = await result
        AuditLog.entries.append((info.python_name, repr(result)))
        return result


def _current_user(ctx: Context):
    return ctx.current_user if isinstance(ctx, AppContext) else None


@Mutation
class Mutations:
    @Field(permission_classes=[IsAuthenticated], extensions=[AuditLog()])
    async def create_post(self, input: CreatePostInput, ctx: Context) -> Post:
        post = STORE.add_post(
            title=input.title,
            body=input.body,
            status=as_status(input.status),
            author=_current_user(ctx),
        )
        await pubsub.publish("post_added", post)
        return post

    @Field(permission_classes=[IsAdmin])
    async def publish_post(self, id: int) -> "Post | None":
        return STORE.set_status(id, PostStatus.PUBLISHED)

    @Field(permission_classes=[IsAuthenticated])
    async def add_comment(self, post_id: int, body: str, ctx: Context) -> Comment:
        comment = STORE.add_comment(
            post_id=post_id, body=body, author=_current_user(ctx)
        )
        await pubsub.publish(f"comment_added:{post_id}", comment)
        return comment


__all__ = ["Mutations", "AuditLog"]
