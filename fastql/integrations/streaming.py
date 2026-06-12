"""Framework-neutral encoders for GraphQL streaming HTTP responses."""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

from fastql.execution import ExecutionResult

MULTIPART_BOUNDARY = "graphql"


async def sse_stream(
    results: AsyncIterable[ExecutionResult | dict[str, Any]],
) -> AsyncIterator[bytes]:
    """Encode execution results (or incremental payload dicts) as Server-Sent Events."""
    try:
        async for result in results:
            payload = _json_bytes(_formatted(result))
            yield b"data: " + payload + b"\n\n"
    finally:
        await _close(results)


async def multipart_stream(
    results: AsyncIterable[ExecutionResult | dict[str, Any]],
    *,
    boundary: str = MULTIPART_BOUNDARY,
) -> AsyncIterator[bytes]:
    """Encode results (or incremental payload dicts) as ``multipart/mixed`` parts."""
    marker = f"--{boundary}".encode("ascii")
    try:
        async for result in results:
            yield (
                marker
                + b"\r\ncontent-type: application/json; charset=utf-8\r\n\r\n"
                + _json_bytes(_formatted(result))
                + b"\r\n"
            )
        yield marker + b"--\r\n"
    finally:
        await _close(results)


def _formatted(item: Any) -> Any:
    """Return the JSON-ready body for an ``ExecutionResult`` or a raw dict payload."""
    formatted = getattr(item, "formatted", None)
    return formatted() if callable(formatted) else item


async def single_result_stream(
    result: ExecutionResult,
) -> AsyncIterator[ExecutionResult]:
    """Adapt an initial subscription error to the streaming encoder contract."""
    yield result


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


async def _close(value: Any) -> None:
    close = getattr(value, "aclose", None)
    if close is not None:
        await close()


__all__ = [
    "MULTIPART_BOUNDARY",
    "multipart_stream",
    "single_result_stream",
    "sse_stream",
]
