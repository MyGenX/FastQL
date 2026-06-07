"""Tests for schema-level lifecycle extensions."""

from __future__ import annotations

import inspect

import pytest

from fastql import Field, Query, Schema, SchemaExtension, build_schema, execute
from fastql.context import default_dependencies
from fastql.decorators import default_registry


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def _schema(extensions):
    @Query
    class Root:
        @Field
        def hello(self) -> str:
            return "hi"

        @Field
        def world(self) -> str:
            return "world"

    return Schema(query=Root, extensions=extensions)


async def test_hooks_fire_in_phase_order():
    class Recorder(SchemaExtension):
        def __init__(self):
            self.events: list[str] = []

        def on_operation(self):
            self.events.append("op:start")
            yield
            self.events.append("op:end")

        def on_parse(self):
            self.events.append("parse:start")
            yield
            self.events.append("parse:end")

        def on_validate(self):
            self.events.append("validate:start")
            yield
            self.events.append("validate:end")

        def on_execute(self):
            self.events.append("execute:start")
            yield
            self.events.append("execute:end")

    rec = Recorder()
    result = await execute(_schema([rec]), "{ hello }")

    assert result.errors == []
    assert rec.events == [
        "op:start",
        "parse:start",
        "parse:end",
        "validate:start",
        "validate:end",
        "execute:start",
        "execute:end",
        "op:end",
    ]


async def test_extensions_compose_first_wraps_later():
    log: list[str] = []

    class Ext(SchemaExtension):
        def __init__(self, label):
            self.label = label

        def on_execute(self):
            log.append(f"{self.label}:start")
            yield
            log.append(f"{self.label}:end")

    await execute(_schema([Ext("A"), Ext("B")]), "{ hello }")

    # A enters before B, exits after B (A wraps B).
    assert log == ["A:start", "B:start", "B:end", "A:end"]


async def test_resolve_wraps_every_field():
    class CountResolves(SchemaExtension):
        def __init__(self):
            self.fields: list[str] = []

        def resolve(self, next_, source, info, **kwargs):
            self.fields.append(info.field_name)
            return next_(source, info, **kwargs)

    counter = CountResolves()
    result = await execute(_schema([counter]), "{ hello world }")

    assert result.errors == []
    assert sorted(counter.fields) == ["hello", "world"]


async def test_resolve_can_transform_result():
    class Shout(SchemaExtension):
        async def resolve(self, next_, source, info, **kwargs):
            result = next_(source, info, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result.upper() if isinstance(result, str) else result

    result = await execute(_schema([Shout()]), "{ hello }")
    assert result.data == {"hello": "HI"}


async def test_async_hook_awaited():
    class AsyncExt(SchemaExtension):
        def __init__(self):
            self.events: list[str] = []

        async def on_execute(self):
            self.events.append("before")
            yield
            self.events.append("after")

    ext = AsyncExt()
    await execute(_schema([ext]), "{ hello }")
    assert ext.events == ["before", "after"]


async def test_get_results_merged_into_extensions():
    class Meta(SchemaExtension):
        def get_results(self):
            return {"meta": {"ok": True}}

    result = await execute(_schema([Meta()]), "{ hello }")
    assert result.extensions == {"meta": {"ok": True}}


async def test_extension_classes_are_instantiated():
    calls: list[str] = []

    class Marker(SchemaExtension):
        def on_operation(self):
            calls.append("ran")
            yield

    # Registered as a class, not an instance.
    await execute(_schema([Marker]), "{ hello }")
    assert calls == ["ran"]


async def test_build_schema_accepts_extensions():
    @Query
    class Root:
        @Field
        def hello(self) -> str:
            return "hi"

    class Meta(SchemaExtension):
        def get_results(self):
            return {"via": "build_schema"}

    schema = build_schema(Root, extensions=[Meta()])
    result = await execute(schema, "{ hello }")
    assert result.extensions == {"via": "build_schema"}


async def test_no_extensions_still_executes():
    result = await execute(_schema([]), "{ hello world }")
    assert result.errors == []
    assert result.data == {"hello": "hi", "world": "world"}
    assert result.extensions is None
