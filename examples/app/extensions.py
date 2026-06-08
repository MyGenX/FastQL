"""Schema-wide lifecycle extensions.

A ``SchemaExtension`` can wrap each phase of an operation and contribute metadata to
``ExecutionResult.extensions``. Two are wired onto the schema:

* :class:`Timing` — wraps the whole operation and reports its wall-clock duration
  under ``extensions.timing``;
* :class:`ResolverCount` — overrides :meth:`resolve` to count field resolutions and
  reports the total under ``extensions.resolverCount``.
"""

from __future__ import annotations

import time

from fastql import SchemaExtension


class Timing(SchemaExtension):
    """Surface each operation's duration under ``extensions.timing``."""

    def on_operation(self):
        self._start = time.perf_counter()
        yield  # the operation runs here
        self._elapsed = time.perf_counter() - self._start

    def get_results(self) -> dict:
        return {"timing": {"duration_ms": round(self._elapsed * 1000, 3)}}


class ResolverCount(SchemaExtension):
    """Count every field resolution in the operation."""

    def __init__(self) -> None:
        self._count = 0

    def resolve(self, next_, source, info, **kwargs):
        self._count += 1
        # ``next_`` is an async continuation; return it so the executor awaits it.
        return next_(source, info, **kwargs)

    def get_results(self) -> dict:
        return {"resolverCount": self._count}


__all__ = ["Timing", "ResolverCount"]
