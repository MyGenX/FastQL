"""Dependency-free Apollo-style tracing instrumentation."""

from __future__ import annotations

import inspect
import time
from datetime import datetime, timezone
from typing import Any

from fastql.extensions import SchemaExtension
from fastql.types import ListType, NonNull


class ApolloTracingExtension(SchemaExtension):
    """Attach Apollo tracing version 1 metadata to execution results."""

    def __init__(self) -> None:
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None
        self._start_ns = 0
        self._end_ns = 0
        self._resolvers: list[dict[str, Any]] = []

    def on_operation(self):
        self._start_time = datetime.now(timezone.utc)
        self._start_ns = time.perf_counter_ns()
        yield
        self._end_ns = time.perf_counter_ns()
        self._end_time = datetime.now(timezone.utc)

    async def resolve(self, next_, source, info, **kwargs):
        start_ns = time.perf_counter_ns()
        try:
            result = next_(source, info, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        finally:
            end_ns = time.perf_counter_ns()
            field = info.parent_type.fields.get(info.field_name)
            self._resolvers.append(
                {
                    "path": list(info.path),
                    "parentType": info.parent_type.name,
                    "fieldName": info.field_name,
                    "returnType": _type_ref(field.type) if field is not None else "",
                    "startOffset": max(0, start_ns - self._start_ns),
                    "duration": end_ns - start_ns,
                }
            )

    def get_results(self) -> dict[str, Any]:
        if self._start_time is None:
            return {}
        end_time = self._end_time or datetime.now(timezone.utc)
        end_ns = self._end_ns or time.perf_counter_ns()
        return {
            "tracing": {
                "version": 1,
                "startTime": _timestamp(self._start_time),
                "endTime": _timestamp(end_time),
                "duration": max(0, end_ns - self._start_ns),
                "execution": {
                    "resolvers": sorted(
                        self._resolvers,
                        key=lambda resolver: resolver["startOffset"],
                    )
                },
            }
        }


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _type_ref(type_: Any) -> str:
    if isinstance(type_, NonNull):
        return _type_ref(type_.of_type) + "!"
    if isinstance(type_, ListType):
        return "[" + _type_ref(type_.of_type) + "]"
    return getattr(type_, "name", str(type_))


__all__ = ["ApolloTracingExtension"]
