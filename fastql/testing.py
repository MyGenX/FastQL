"""A native test client for executing operations against a schema.

``GraphQLTestClient`` wraps :func:`~fastql.execution.execute` and
:func:`~fastql.execution.subscribe` so tests can run queries, mutations, and
subscriptions directly against a schema — no HTTP layer required.

    client = GraphQLTestClient(schema, context=make_context())
    result = await client.execute("{ user(id: 1) { name } }")
    assert result.errors == []

    async for event in client.subscribe("subscription { counter(to: 3) }"):
        ...
"""

from __future__ import annotations

from typing import Any

from fastql.execution import ExecutionResult
from fastql.execution import execute as _execute
from fastql.execution import subscribe as _subscribe

_UNSET = object()


class GraphQLTestClient:
    """Execute operations against a schema for testing.

    A default ``context`` may be supplied at construction and overridden per
    call. ``execute`` returns the :class:`~fastql.execution.ExecutionResult`;
    ``subscribe`` is an async generator yielding one result per event.
    """

    def __init__(self, schema: Any, context: Any = None) -> None:
        self.schema = schema
        self.default_context = context

    async def execute(
        self,
        query: str,
        *,
        variable_values: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any = _UNSET,
        root_value: Any = None,
        mask_errors: bool = False,
    ) -> ExecutionResult:
        """Run a query or mutation and return its ``ExecutionResult``."""
        return await _execute(
            self.schema,
            query,
            variable_values=variable_values,
            context=self._context(context),
            operation_name=operation_name,
            root_value=root_value,
            mask_errors=mask_errors,
        )

    async def subscribe(
        self,
        query: str,
        *,
        variable_values: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any = _UNSET,
        root_value: Any = None,
        mask_errors: bool = False,
    ):
        """Subscribe and yield each ``ExecutionResult`` from the stream.

        If the subscription fails to start, the single initial error result is
        yielded once.
        """
        stream = await _subscribe(
            self.schema,
            query,
            variable_values=variable_values,
            context=self._context(context),
            operation_name=operation_name,
            root_value=root_value,
            mask_errors=mask_errors,
        )
        if isinstance(stream, ExecutionResult):
            yield stream
            return
        async for result in stream:
            yield result

    def _context(self, context: Any) -> Any:
        return self.default_context if context is _UNSET else context


__all__ = ["GraphQLTestClient"]
