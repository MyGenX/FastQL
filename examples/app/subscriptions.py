"""Root subscriptions.

A ``@Subscription`` field is an ``async def`` that ``yield``s — i.e. an async generator
whose yielded type is the GraphQL field type. The core ``subscribe()`` API drives it and
emits one ``ExecutionResult`` per yielded value. Here each subscription tails a pub/sub
topic that the mutations publish to.

Live transport (WebSocket/SSE) is not implemented yet, so these are consumed via
``subscribe()`` / ``GraphQLTestClient.subscribe()`` — see ``examples/app/demo.py``.
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastql import Field, Subscription

from examples.app.pubsub import pubsub
from examples.app.types import Comment, Post


@Subscription
class Subscriptions:
    @Field
    async def post_added(self) -> AsyncGenerator[Post, None]:
        async for post in pubsub.subscribe("post_added"):
            yield post

    @Field
    async def comment_added(self, post_id: int) -> AsyncGenerator[Comment, None]:
        async for comment in pubsub.subscribe(f"comment_added:{post_id}"):
            yield comment


__all__ = ["Subscriptions"]
