"""Tests for the request-scoped DataLoader (N+1 mitigation)."""

from __future__ import annotations

import asyncio

import pytest

from fastql import Context, DataLoader, DataLoaderError, get_loader


def _recording_loader(**kwargs):
    """A loader whose batch fn records each batch and returns key * 10."""
    calls: list[list[int]] = []

    async def batch(keys):
        calls.append(list(keys))
        return [key * 10 for key in keys]

    return DataLoader(batch, **kwargs), calls


async def test_keys_in_same_tick_are_batched():
    loader, calls = _recording_loader()

    f1 = loader.load(1)
    f2 = loader.load(2)
    r1, r2 = await asyncio.gather(f1, f2)

    assert (r1, r2) == (10, 20)
    assert calls == [[1, 2]]  # one batched call


async def test_load_many_returns_aligned_results():
    loader, calls = _recording_loader()

    results = await loader.load_many([3, 1, 2])

    assert results == [30, 10, 20]
    assert calls == [[3, 1, 2]]


async def test_duplicate_keys_deduplicated():
    loader, calls = _recording_loader()

    f1 = loader.load(1)
    f2 = loader.load(1)
    r1, r2 = await asyncio.gather(f1, f2)

    assert r1 == r2 == 10
    assert calls == [[1]]  # key appears once


async def test_cache_returns_same_result_without_refetch():
    loader, calls = _recording_loader()

    first = await loader.load(1)
    second = await loader.load(1)

    assert first == second == 10
    assert calls == [[1]]  # second load served from cache


async def test_max_batch_size_chunks_keys():
    loader, calls = _recording_loader(max_batch_size=2)

    await loader.load_many([1, 2, 3])

    assert calls == [[1, 2], [3]]


async def test_clear_forces_refetch():
    loader, calls = _recording_loader()

    await loader.load(1)
    loader.clear(1)
    await loader.load(1)

    assert calls == [[1], [1]]


async def test_clear_all_drops_every_key():
    loader, calls = _recording_loader()

    await loader.load_many([1, 2])
    loader.clear_all()
    await loader.load(1)

    assert calls == [[1, 2], [1]]


async def test_prime_seeds_cache_without_batch_call():
    loader, calls = _recording_loader()

    loader.prime(1, 999)
    value = await loader.load(1)

    assert value == 999
    assert calls == []  # batch fn never invoked


async def test_per_key_error_isolated():
    async def batch(keys):
        return [ValueError("bad 2") if key == 2 else key * 10 for key in keys]

    loader = DataLoader(batch)

    f1 = loader.load(1)
    f2 = loader.load(2)
    results = await asyncio.gather(f1, f2, return_exceptions=True)

    assert results[0] == 10
    assert isinstance(results[1], ValueError)


async def test_batch_function_raising_fails_all_keys():
    async def batch(keys):
        raise RuntimeError("boom")

    loader = DataLoader(batch)

    results = await asyncio.gather(
        loader.load(1), loader.load(2), return_exceptions=True
    )

    assert all(isinstance(r, RuntimeError) for r in results)


async def test_per_key_error_is_cached():
    # An Error *element* in the result list is a per-key failure and is cached,
    # matching DataLoader semantics.
    attempts: list[list[int]] = []

    async def batch(keys):
        attempts.append(list(keys))
        return [ValueError("nope") for _ in keys]

    loader = DataLoader(batch)

    with pytest.raises(ValueError):
        await loader.load(1)
    with pytest.raises(ValueError):
        await loader.load(1)

    assert attempts == [[1]]  # second load served from the cached rejection


async def test_batch_failure_allows_retry():
    # When the batch function *raises*, the keys are evicted so a later load
    # can retry rather than being stuck with a poisoned cache entry.
    attempts: list[list[int]] = []

    async def batch(keys):
        attempts.append(list(keys))
        if len(attempts) == 1:
            raise RuntimeError("transient")
        return [key * 10 for key in keys]

    loader = DataLoader(batch)

    with pytest.raises(RuntimeError):
        await loader.load(1)
    assert await loader.load(1) == 10
    assert attempts == [[1], [1]]


async def test_wrong_length_result_errors():
    async def batch(keys):
        return [1]  # too few

    loader = DataLoader(batch)

    with pytest.raises(DataLoaderError):
        await loader.load_many([1, 2])


def test_invalid_max_batch_size_rejected():
    async def batch(keys):
        return keys

    with pytest.raises(ValueError):
        DataLoader(batch, max_batch_size=0)


async def test_get_loader_is_request_scoped():
    async def batch(keys):
        return list(keys)

    class AppContext(Context):
        pass

    ctx = AppContext()
    a = get_loader(ctx, batch)
    b = get_loader(ctx, batch)
    assert a is b  # same loader shared within one context

    other = AppContext()
    assert get_loader(other, batch) is not a  # separate request, separate loader


async def test_get_loader_accepts_info_like_holder():
    async def batch(keys):
        return list(keys)

    class AppContext(Context):
        pass

    class FakeInfo:
        # Not a fastql.Info instance, but exposes .context — get_loader uses the
        # holder directly here since isinstance(holder, Info) is False.
        def __init__(self, context):
            self.context = context

    ctx = AppContext()
    # A real Info would unwrap to .context; a plain object is used as-is.
    holder = FakeInfo(ctx)
    loader = get_loader(holder, batch)
    assert get_loader(holder, batch) is loader
