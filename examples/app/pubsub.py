"""A tiny in-process async pub/sub backing the subscriptions.

Mutations publish to a topic; subscription resolvers consume it as an async generator.
A production deployment would swap this for Redis / NATS / Postgres LISTEN, but the
subscription resolvers in :mod:`examples.app.subscriptions` would not change.

This is *not* a transport — FastQL's live subscription transport (WebSocket/SSE) is not
implemented yet, so subscriptions here are exercised through the core ``subscribe()`` API
and ``GraphQLTestClient`` (see ``examples/app/demo.py``), not over HTTP.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncGenerator


class PubSub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, topic: str, message) -> None:
        for queue in list(self._subscribers[topic]):
            queue.put_nowait(message)

    async def subscribe(self, topic: str) -> AsyncGenerator:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[topic].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[topic].discard(queue)

    def has_subscribers(self, topic: str) -> bool:
        return bool(self._subscribers.get(topic))


#: The process-wide pub/sub used by mutations and subscriptions.
pubsub = PubSub()

__all__ = ["PubSub", "pubsub"]
