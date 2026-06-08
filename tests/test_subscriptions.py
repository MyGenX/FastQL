"""Tests for async-generator subscription execution."""

from __future__ import annotations

from typing import AsyncGenerator

import pytest

from fastql import (
    Context,
    Field,
    Query,
    Schema,
    Subscription,
    Type,
    execute,
    subscribe,
)
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.execution import ExecutionResult


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def _query_only_root():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    return Q


async def _collect(stream):
    return [result async for result in stream]


async def test_stream_yields_a_result_per_event():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def counter(self, to: int) -> AsyncGenerator[int, None]:
            for i in range(to):
                yield i

    schema = Schema(query=Q, subscription=Sub)
    stream = await subscribe(schema, "subscription { counter(to: 3) }")

    results = await _collect(stream)
    assert [r.data for r in results] == [
        {"counter": 0},
        {"counter": 1},
        {"counter": 2},
    ]
    assert all(r.errors == [] for r in results)


async def test_subscription_field_can_yield_objects():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Type
    class Message:
        body: str

    @Subscription
    class Sub:
        @Field
        async def messages(self) -> AsyncGenerator[Message, None]:
            yield Message("hello")
            yield Message("world")

    schema = Schema(query=Q, subscription=Sub)
    stream = await subscribe(schema, "subscription { messages { body } }")

    results = await _collect(stream)
    assert [r.data for r in results] == [
        {"messages": {"body": "hello"}},
        {"messages": {"body": "world"}},
    ]


async def test_more_than_one_root_field_is_rejected():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def a(self) -> AsyncGenerator[int, None]:
            yield 1

        @Field
        async def b(self) -> AsyncGenerator[int, None]:
            yield 2

    schema = Schema(query=Q, subscription=Sub)
    result = await subscribe(schema, "subscription { a b }")

    assert isinstance(result, ExecutionResult)
    assert result.executed is False
    assert any("exactly one root field" in e.message for e in result.errors)


async def test_subscribe_rejects_non_subscription_operation():
    schema = Schema(query=_query_only_root())
    result = await subscribe(schema, "{ ping }")

    assert isinstance(result, ExecutionResult)
    assert result.executed is False
    assert any("requires a subscription" in e.message for e in result.errors)


async def test_initial_error_when_resolver_raises_before_yield():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def boom(self) -> AsyncGenerator[int, None]:
            # An async def without a yield is a coroutine: it raises on call,
            # before any stream is produced.
            raise ValueError("setup failed")

    schema = Schema(query=Q, subscription=Sub)
    result = await subscribe(schema, "subscription { boom }")

    assert isinstance(result, ExecutionResult)
    assert result.executed is False
    assert any("setup failed" in e.message for e in result.errors)


async def test_validation_error_returns_single_result():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def counter(self) -> AsyncGenerator[int, None]:
            yield 1

    schema = Schema(query=Q, subscription=Sub)
    result = await subscribe(schema, "subscription { nope }")

    assert isinstance(result, ExecutionResult)
    assert result.executed is False
    assert any("nope" in e.message for e in result.errors)


async def test_per_event_resolver_errors_are_isolated():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Type
    class Item:
        @Field
        def value(self, n: int) -> "int | None":  # nullable: error stays local
            if n == 1:
                raise ValueError("bad event")
            return n

    @Subscription
    class Sub:
        @Field
        async def items(self) -> AsyncGenerator[Item, None]:
            for _ in range(3):
                yield Item()

    schema = Schema(query=Q, subscription=Sub)
    stream = await subscribe(schema, "subscription { items { value(n: 1) } }")
    results = await _collect(stream)

    # Three events; each one's `value` resolver raised, isolated per result.
    assert len(results) == 3
    for r in results:
        assert r.data == {"items": {"value": None}}
        assert any("bad event" in e.message for e in r.errors)


async def test_generator_closed_on_consumer_cancel():
    closed = {"value": False}

    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def forever(self) -> AsyncGenerator[int, None]:
            try:
                i = 0
                while True:
                    yield i
                    i += 1
            finally:
                closed["value"] = True

    schema = Schema(query=Q, subscription=Sub)
    stream = await subscribe(schema, "subscription { forever }")

    first = await stream.__anext__()
    assert first.data == {"forever": 0}

    await stream.aclose()  # consumer stops early
    assert closed["value"] is True


async def test_source_stream_error_yields_error_result_and_stops():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Subscription
    class Sub:
        @Field
        async def flaky(self) -> AsyncGenerator[int, None]:
            yield 1
            raise RuntimeError("stream broke")

    schema = Schema(query=Q, subscription=Sub)
    stream = await subscribe(schema, "subscription { flaky }")
    results = await _collect(stream)

    assert results[0].data == {"flaky": 1}
    assert any("stream broke" in e.message for e in results[-1].errors)


async def test_execute_still_runs_queries():
    # Subscription support must not disturb the normal query path.
    schema = Schema(query=_query_only_root())
    result = await execute(schema, "{ ping }")
    assert result.data == {"ping": "pong"}
