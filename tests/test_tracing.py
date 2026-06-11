"""Apollo tracing and optional OpenTelemetry instrumentation tests."""

from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from fastql import (
    ApolloTracingExtension,
    Field,
    Query,
    Schema,
    execute,
)
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.opentelemetry import OpenTelemetryExtension

ROOT = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def make_schema(extensions):
    @Query
    class Q:
        @Field
        def hello(self) -> str:
            return "hello"

        @Field
        def fail(self) -> str | None:
            raise RuntimeError("resolver failed")

    return Schema(query=Q, extensions=extensions)


async def test_apollo_tracing_block_contains_operation_and_resolver_timing():
    result = await execute(
        make_schema([ApolloTracingExtension]),
        "query Traced { hello }",
    )

    tracing = result.extensions["tracing"]
    assert tracing["version"] == 1
    assert tracing["startTime"].endswith("Z")
    assert tracing["endTime"].endswith("Z")
    assert tracing["duration"] >= 0
    resolver = tracing["execution"]["resolvers"][0]
    assert resolver["path"] == ["hello"]
    assert resolver["parentType"] == "Query"
    assert resolver["fieldName"] == "hello"
    assert resolver["returnType"] == "String!"
    assert resolver["startOffset"] >= 0
    assert resolver["duration"] >= 0


async def test_apollo_tracing_is_returned_for_validation_errors():
    result = await execute(
        make_schema([ApolloTracingExtension]),
        "query Invalid { missing }",
    )

    assert result.errors
    assert result.extensions["tracing"]["execution"]["resolvers"] == []


class FakeSpan:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.attributes = {}
        self.exceptions = []

    def update_name(self, name):
        self.name = name

    def set_attribute(self, name, value):
        self.attributes[name] = value

    def record_exception(self, error):
        self.exceptions.append(error)


class FakeTracer:
    def __init__(self):
        self.spans = []
        self.stack = []

    @contextmanager
    def start_as_current_span(self, name):
        parent = self.stack[-1] if self.stack else None
        span = FakeSpan(name, parent)
        self.spans.append(span)
        self.stack.append(span)
        try:
            yield span
        finally:
            assert self.stack.pop() is span


async def test_opentelemetry_emits_operation_and_child_field_spans():
    tracer = FakeTracer()
    result = await execute(
        make_schema([OpenTelemetryExtension(tracer=tracer)]),
        "query Traced { hello }",
    )

    assert result.errors == []
    assert len(tracer.spans) == 2
    operation, field = tracer.spans
    assert operation.name == "GraphQL query Traced"
    assert operation.attributes == {
        "graphql.operation.type": "query",
        "graphql.operation.name": "Traced",
    }
    assert field.parent is operation
    assert field.name == "GraphQL field Query.hello"
    assert field.attributes["graphql.field.name"] == "hello"
    assert field.attributes["graphql.field.path"] == "hello"
    assert field.attributes["graphql.operation.name"] == "Traced"


async def test_opentelemetry_records_resolver_errors():
    tracer = FakeTracer()
    result = await execute(
        make_schema([OpenTelemetryExtension(tracer=tracer)]),
        "query Broken { fail }",
    )

    assert result.errors
    operation, field = tracer.spans
    assert isinstance(field.exceptions[0], RuntimeError)
    assert isinstance(operation.exceptions[0], RuntimeError)
    assert field.attributes["error.type"] == "RuntimeError"


def test_core_runs_when_opentelemetry_is_unavailable():
    code = """
import builtins
import asyncio
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'opentelemetry' or name.startswith('opentelemetry.'):
        raise ImportError('blocked for test')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
import fastql

@fastql.Query
class Q:
    @fastql.Field
    def ping(self) -> str:
        return 'pong'

result = asyncio.run(fastql.execute(fastql.Schema(query=Q), '{ ping }'))
assert result.data == {'ping': 'pong'}
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_default_opentelemetry_extension_requires_extra():
    code = """
import builtins
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'opentelemetry' or name.startswith('opentelemetry.'):
        raise ImportError('blocked for test')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
from fastql.opentelemetry import OpenTelemetryExtension
try:
    OpenTelemetryExtension()
except ImportError as error:
    assert 'mygenx-fastql[opentelemetry]' in str(error)
else:
    raise AssertionError('missing optional dependency was accepted')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
