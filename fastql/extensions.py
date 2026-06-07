"""Schema-level lifecycle extensions.

A :class:`SchemaExtension` observes (and can wrap) each phase of operation
handling — ``on_operation`` (outermost), then ``on_parse``, ``on_validate``,
``on_execute`` — plus every field ``resolve`` call. Each phase hook may run code
*before* and *after* its phase by ``yield``-ing once (generator style); a plain
or ``async`` hook that does not yield runs only before the phase.

    class Timing(SchemaExtension):
        def on_operation(self):
            self._start = time.perf_counter()
            yield                       # operation runs here
            self._elapsed = time.perf_counter() - self._start

        def get_results(self):
            return {"timing": {"duration": self._elapsed}}

    schema = Schema(query=Query, extensions=[Timing])

Extensions are registered on the schema as instances or classes (classes are
instantiated once per :func:`~fastql.execution.execute` call). This module is
part of the dependency-free core and imports no web framework.
"""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Iterable, Sequence

NextResolver = Callable[..., Any]


class SchemaExtension:
    """Base class for schema lifecycle extensions.

    Override any subset of the phase hooks and/or :meth:`resolve`. Phase hooks
    may ``yield`` once to wrap the phase; otherwise they run before it. Both sync
    and ``async`` implementations are supported.
    """

    def on_operation(self) -> Any:  # noqa: D401 - hook
        """Wrap the whole operation."""
        return None

    def on_parse(self) -> Any:
        """Wrap document parsing."""
        return None

    def on_validate(self) -> Any:
        """Wrap validation."""
        return None

    def on_execute(self) -> Any:
        """Wrap execution."""
        return None

    def resolve(self, next_: NextResolver, source: Any, info: Any, **kwargs: Any) -> Any:
        """Wrap a single field resolution. Call ``next_`` to continue."""
        return next_(source, info, **kwargs)

    def get_results(self) -> dict[str, Any]:
        """Return metadata to merge into ``ExecutionResult.extensions``."""
        return {}


#: Hook names in nesting order (outermost first).
PHASES = ("on_operation", "on_parse", "on_validate", "on_execute")


def instantiate_extensions(
    extensions: Iterable[Any] | None,
) -> list[SchemaExtension]:
    """Turn a list of extension instances/classes into instances."""
    if not extensions:
        return []
    return [ext() if isinstance(ext, type) else ext for ext in extensions]


async def _enter(result: Any) -> tuple[str, Any] | None:
    """Run the 'before' portion of a hook result; return a finalizer token."""
    if result is None:
        return None
    if inspect.isasyncgen(result):
        await result.__anext__()
        return ("agen", result)
    if inspect.isgenerator(result):
        next(result)
        return ("gen", result)
    if inspect.isawaitable(result):
        await result
        return None
    return None


async def _finalize(token: tuple[str, Any]) -> None:
    """Run the 'after' portion for a generator-style hook."""
    kind, gen = token
    if kind == "agen":
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
    else:
        try:
            next(gen)
        except StopIteration:
            pass


@asynccontextmanager
async def phase(extensions: Sequence[SchemaExtension], hook_name: str):
    """Async context manager running ``hook_name`` around a phase.

    Extensions enter in registration order and exit in reverse, so the first
    registered extension wraps the later ones.
    """
    finalizers: list[tuple[str, Any]] = []
    for ext in extensions:
        hook = getattr(ext, hook_name, None)
        if hook is None:
            continue
        token = await _enter(hook())
        if token is not None:
            finalizers.append(token)
    try:
        yield
    finally:
        for token in reversed(finalizers):
            await _finalize(token)


def has_resolve_override(ext: SchemaExtension) -> bool:
    """True if ``ext`` overrides :meth:`resolve` (skips the no-op fast path)."""
    return type(ext).resolve is not SchemaExtension.resolve


async def collect_results(extensions: Sequence[SchemaExtension]) -> dict[str, Any]:
    """Merge every extension's ``get_results`` into one mapping."""
    merged: dict[str, Any] = {}
    for ext in extensions:
        results = ext.get_results()
        if inspect.isawaitable(results):
            results = await results
        if results:
            merged.update(results)
    return merged


__all__ = [
    "SchemaExtension",
    "PHASES",
    "instantiate_extensions",
    "phase",
    "has_resolve_override",
    "collect_results",
]
