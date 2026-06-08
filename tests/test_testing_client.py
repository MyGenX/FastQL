"""Tests for the GraphQLTestClient testing utility."""

from __future__ import annotations

from typing import AsyncGenerator

import pytest

from fastql import (
    Context,
    Field,
    GraphQLTestClient,
    Query,
    Schema,
    Subscription,
)
from fastql.context import default_dependencies
from fastql.decorators import default_registry


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


async def test_execute_returns_result():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    client = GraphQLTestClient(Schema(query=Q))
    result = await client.execute("{ ping }")

    assert result.errors == []
    assert result.data == {"ping": "pong"}


async def test_execute_passes_variables():
    @Query
    class Q:
        @Field
        def echo(self, value: int) -> int:
            return value

    client = GraphQLTestClient(Schema(query=Q))
    result = await client.execute(
        "query ($v: Int!) { echo(value: $v) }", variable_values={"v": 7}
    )
    assert result.data == {"echo": 7}


async def test_context_supplied_to_resolvers():
    class AppContext(Context):
        def __init__(self, who: str):
            self.who = who

    @Query
    class Q:
        @Field
        def greeting(self, ctx: Context) -> str:
            return f"hi {ctx.who}"

    client = GraphQLTestClient(Schema(query=Q), context=AppContext("ada"))
    result = await client.execute("{ greeting }")
    assert result.data == {"greeting": "hi ada"}


async def test_per_call_context_overrides_default():
    class AppContext(Context):
        def __init__(self, who: str):
            self.who = who

    @Query
    class Q:
        @Field
        def greeting(self, ctx: Context) -> str:
            return f"hi {ctx.who}"

    client = GraphQLTestClient(Schema(query=Q), context=AppContext("default"))
    result = await client.execute("{ greeting }", context=AppContext("override"))
    assert result.data == {"greeting": "hi override"}


async def test_subscribe_collects_results():
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

    client = GraphQLTestClient(Schema(query=Q, subscription=Sub))
    results = [r async for r in client.subscribe("subscription { counter(to: 3) }")]

    assert [r.data for r in results] == [
        {"counter": 0},
        {"counter": 1},
        {"counter": 2},
    ]


async def test_subscribe_yields_initial_error_once():
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

    client = GraphQLTestClient(Schema(query=Q, subscription=Sub))
    results = [r async for r in client.subscribe("subscription { nope }")]

    assert len(results) == 1
    assert results[0].executed is False
    assert results[0].errors
