"""Synchronous adapter bridge for the async-first FastQL handler."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, TypeVar

T = TypeVar("T")


def run_sync(awaitable: Awaitable[T]) -> T:
    """Run an awaitable from sync code, including inside a running event loop."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, awaitable).result()


__all__ = ["run_sync"]
