"""Framework-neutral encoders for GraphQL streaming HTTP responses."""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

from fastql.execution import ExecutionResult

MULTIPART_BOUNDARY = "graphql"


async def sse_stream(results: AsyncIterable[ExecutionResult]) -> AsyncIterator[bytes]:
    """Encode execution results as Server-Sent Events."""
    try:
        async for result in results:
            payload = _json_bytes(result.formatted())
            yield b"data: " + payload + b"\n\n"
    finally:
        await _close(results)


async def multipart_stream(
    results: AsyncIterable[ExecutionResult],
    *,
    boundary: str = MULTIPART_BOUNDARY,
) -> AsyncIterator[bytes]:
    """Encode execution results as ``multipart/mixed`` response parts."""
    marker = f"--{boundary}".encode("ascii")
    try:
        async for result in results:
            yield (
                marker
                + b"\r\ncontent-type: application/json; charset=utf-8\r\n\r\n"
                + _json_bytes(result.formatted())
                + b"\r\n"
            )
        yield marker + b"--\r\n"
    finally:
        await _close(results)


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
