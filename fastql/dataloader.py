"""Request-scoped batch loading to eliminate N+1 resolver fan-out.

A :class:`DataLoader` coalesces individual :meth:`~DataLoader.load` calls made
within the same event-loop tick into a single call to a user-supplied async batch
function, then fans the results back out to the awaiting callers. Results are
cached per key for the loader's lifetime, so a loader created per request gives
request-scoped caching without leaking across requests.

    async def batch_users(ids: list[int]) -> list[User]:
        rows = await db.fetch_users(ids)
        by_id = {r.id: r for r in rows}
        return [by_id.get(i) for i in ids]

    loader = DataLoader(batch_users)
    a, b = await asyncio.gather(loader.load(1), loader.load(2))  # one DB call

Use :func:`get_loader` to lazily create and reuse a loader stored on the active
:class:`~fastql.context.Context` (or :class:`~fastql.context.Info`).
"""

from __future__ import annotations

import asyncio
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Hashable,
    Sequence,
    TypeVar,
)

from fastql.context import Context, Info

K = TypeVar("K")
V = TypeVar("V")

#: An async function that, given a list of keys, returns a sequence of results
#: positionally aligned to those keys. An element may be a ``BaseException`` to
#: signal a per-key failure.
BatchLoadFn = Callable[[list[K]], Awaitable[Sequence[Any]]]


class DataLoaderError(RuntimeError):
    """Raised when a batch function returns a result of the wrong shape."""


class DataLoader(Generic[K, V]):
    """Batches and caches keyed lookups for a single request.

    Parameters
    ----------
    batch_load_fn:
        Async function called with a list of keys; must return a sequence of the
        same length, aligned to the keys. An element that is a ``BaseException``
        instance fails only that key's :meth:`load`.
    max_batch_size:
        If set, keys queued in one tick are dispatched in chunks of at most this
        size.
    cache:
        When ``True`` (default) results are cached by key for the loader's life.
    cache_key_fn:
        Maps a key to its cache key (use when keys are unhashable or need
        normalizing). Defaults to the identity function.
    """

    def __init__(
        self,
        batch_load_fn: BatchLoadFn,
        *,
        max_batch_size: int | None = None,
        cache: bool = True,
        cache_key_fn: Callable[[K], Hashable] | None = None,
    ) -> None:
        if max_batch_size is not None and max_batch_size < 1:
            raise ValueError("max_batch_size must be a positive integer")
        self._batch_load_fn = batch_load_fn
        self._max_batch_size = max_batch_size
        self._cache_enabled = cache
        self._cache_key_fn = cache_key_fn or (lambda key: key)
        self._cache: dict[Hashable, asyncio.Future] = {}
        self._queue: list[tuple[K, asyncio.Future]] = []
        self._dispatch_scheduled = False

    # -- public API -----------------------------------------------------------

    def load(self, key: K) -> Awaitable[V]:
        """Return an awaitable for ``key``, batching it with sibling loads."""
        cache_key = self._cache_key_fn(key)
        if self._cache_enabled:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._queue.append((key, future))
        if self._cache_enabled:
            self._cache[cache_key] = future
        if not self._dispatch_scheduled:
            self._dispatch_scheduled = True
            loop.call_soon(self._dispatch)
        return future

    def load_many(self, keys: Sequence[K]) -> Awaitable[list[V]]:
        """Return an awaitable list of results aligned to ``keys``."""
        return asyncio.gather(*(self.load(key) for key in keys))

    def clear(self, key: K) -> "DataLoader[K, V]":
        """Drop ``key`` from the cache so the next load re-fetches it."""
        self._cache.pop(self._cache_key_fn(key), None)
        return self

    def clear_all(self) -> "DataLoader[K, V]":
        """Drop every cached key."""
        self._cache.clear()
        return self

    def prime(self, key: K, value: V | BaseException) -> "DataLoader[K, V]":
        """Seed the cache for ``key`` without calling the batch function.

        Does nothing if ``key`` is already cached (matching DataLoader
        semantics). Pass a ``BaseException`` to prime a failure.
        """
        cache_key = self._cache_key_fn(key)
        if not self._cache_enabled or cache_key in self._cache:
            return self
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        if isinstance(value, BaseException):
            future.set_exception(value)
            # Avoid "exception never retrieved" warnings if never awaited.
            future.add_done_callback(lambda f: f.exception())
        else:
            future.set_result(value)
        self._cache[cache_key] = future
        return self

    # -- internals ------------------------------------------------------------

    def _dispatch(self) -> None:
        self._dispatch_scheduled = False
        queue, self._queue = self._queue, []
        if not queue:
            return
        size = self._max_batch_size
        if size and len(queue) > size:
            for start in range(0, len(queue), size):
                self._dispatch_batch(queue[start : start + size])
        else:
            self._dispatch_batch(queue)

    def _dispatch_batch(self, batch: list[tuple[K, asyncio.Future]]) -> None:
        keys = [key for key, _ in batch]
        futures = [future for _, future in batch]
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_batch(keys, futures))

    async def _run_batch(
        self, keys: list[K], futures: list[asyncio.Future]
    ) -> None:
        try:
            results = list(await self._batch_load_fn(keys))
        except Exception as exc:  # noqa: BLE001 - propagate to every key
            self._fail_pending(futures, exc, keys)
            return
        if len(results) != len(keys):
            self._fail_pending(
                futures,
                DataLoaderError(
                    "batch function returned "
                    f"{len(results)} results for {len(keys)} keys"
                ),
                keys,
            )
            return
        for future, result in zip(futures, results):
            if future.done():
                continue
            if isinstance(result, BaseException):
                future.set_exception(result)
            else:
                future.set_result(result)

    def _fail_pending(
        self, futures: list[asyncio.Future], exc: BaseException, keys: list[K]
    ) -> None:
        for future, key in zip(futures, keys):
            if not future.done():
                future.set_exception(exc)
            # The result is poisoned; drop it so a retry can re-fetch.
            if self._cache_enabled:
                self._cache.pop(self._cache_key_fn(key), None)


# -- request-scoped access ----------------------------------------------------

_LOADER_STORE_ATTR = "_fastql_loaders"


def get_loader(
    holder: Context | Info | Any,
    batch_load_fn: BatchLoadFn,
    **kwargs: Any,
) -> DataLoader:
    """Get or create a request-scoped :class:`DataLoader` on ``holder``.

    ``holder`` may be a :class:`~fastql.context.Context`, an
    :class:`~fastql.context.Info` (its ``context`` is used), or any object that
    can hold an attribute. Loaders are keyed by ``batch_load_fn`` and reused for
    the lifetime of that context, so all resolvers in one request share a loader
    (and its cache); separate requests get separate loaders.
    """
    context = holder.context if isinstance(holder, Info) else holder
    store = getattr(context, _LOADER_STORE_ATTR, None)
    if store is None:
        store = {}
        try:
            setattr(context, _LOADER_STORE_ATTR, store)
        except Exception:  # noqa: BLE001 - immutable context: no sharing
            return DataLoader(batch_load_fn, **kwargs)
    loader = store.get(batch_load_fn)
    if loader is None:
        loader = DataLoader(batch_load_fn, **kwargs)
        store[batch_load_fn] = loader
    return loader


__all__ = ["DataLoader", "DataLoaderError", "BatchLoadFn", "get_loader"]
