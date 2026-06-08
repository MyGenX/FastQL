"""Runnable tour of the showcase: ``python -m examples.app.demo``.

Exercises, against the in-memory schema and without any web framework:

1. a query spanning objects, computed fields, an enum, a union, and DI;
2. a mutation guarded by a permission;
3. a subscription consumed through the core ``subscribe()`` API, fed by the mutation.

It also prints the DataLoader batch log to show that ``users { posts }`` triggers a
single batched load (``[[1, 2]]``) rather than one query per user.
"""

from __future__ import annotations

import asyncio

from fastql import execute, subscribe

from examples.app import make_context, reseed, schema
from examples.app.loaders import BATCH_CALLS
from examples.app.pubsub import pubsub

QUERY = """
{
  me { name role }
  users {
    name
    loudName
    posts { title status }
  }
  search(term: "ada") {
    __typename
    ... on User { name }
    ... on Post { title }
  }
  serverTime
}
"""

CREATE_POST = """
mutation {
  createPost(input: { title: "Live from the demo", body: "..." }) {
    id
    title
    status
    author { name }
  }
}
"""


async def main() -> None:
    reseed()
    ctx = make_context()  # signed in as Ada (admin)

    print("== query ==")
    BATCH_CALLS.clear()
    result = await execute(schema, QUERY, context=ctx)
    print("data:", result.data)
    print("extensions:", result.extensions)
    print("dataloader batch calls:", BATCH_CALLS, "(one batch for all users)")

    print("\n== subscription fed by a mutation ==")
    received: list = []

    stream = await subscribe(schema, "subscription { postAdded { title author { name } } }")

    async def consume() -> None:
        async for event in stream:
            received.append(event.data)
            break

    consumer = asyncio.create_task(consume())
    while not pubsub.has_subscribers("post_added"):  # wait until the stream is live
        await asyncio.sleep(0)

    mutation = await execute(schema, CREATE_POST, context=ctx)
    print("mutation:", mutation.data)

    await consumer
    await stream.aclose()
    print("subscription received:", received)


if __name__ == "__main__":
    asyncio.run(main())
