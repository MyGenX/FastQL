"""Optional OpenTelemetry schema instrumentation.

Install ``mygenx-fastql[opentelemetry]`` or inject a compatible tracer into
``OpenTelemetryExtension``.
"""

from __future__ import annotations

import inspect
from typing import Any

from fastql.extensions import SchemaExtension


class OpenTelemetryExtension(SchemaExtension):
    """Emit one operation span and a child span for each resolved field."""

    def __init__(self, tracer: Any = None) -> None:
        self._status = None
        self._status_code = None
        if tracer is None:
            try:
                from opentelemetry import trace
                from opentelemetry.trace import Status, StatusCode
            except ImportError as error:
                raise ImportError(
                    "OpenTelemetry instrumentation requires "
                    "'mygenx-fastql[opentelemetry]'."
                ) from error
            tracer = trace.get_tracer("fastql", "0.0.1")
            self._status = Status
            self._status_code = StatusCode
        self.tracer = tracer
        self._operation_span = None

    def on_operation(self):
        requested_name = _requested_operation_name(self.execution_context)
        initial_name = f"GraphQL operation {requested_name or '<anonymous>'}"
        with self.tracer.start_as_current_span(initial_name) as span:
            self._operation_span = span
            yield
            operation_type, operation_name = _operation_details(
                self.execution_context
            )
            span.update_name(
                f"GraphQL {operation_type} {operation_name or '<anonymous>'}"
            )
            span.set_attribute("graphql.operation.type", operation_type)
            if operation_name is not None:
                span.set_attribute("graphql.operation.name", operation_name)
            result = getattr(self.execution_context, "result", None)
            for error in getattr(result, "errors", ()):
                self._record_error(span, error)

    async def resolve(self, next_, source, info, **kwargs):
        parent_name = info.parent_type.name
        operation_type, operation_name = _operation_details_from_info(info)
        with self.tracer.start_as_current_span(
            f"GraphQL field {parent_name}.{info.field_name}"
        ) as span:
            span.set_attribute("graphql.field.name", info.field_name)
            span.set_attribute("graphql.field.parent_type", parent_name)
            span.set_attribute(
                "graphql.field.path", ".".join(str(value) for value in info.path)
            )
            span.set_attribute("graphql.operation.type", operation_type)
            if operation_name is not None:
                span.set_attribute("graphql.operation.name", operation_name)
            try:
                result = next_(source, info, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
                return result
            except BaseException as error:
                self._record_error(span, error)
                raise

    def _record_error(self, span: Any, error: BaseException) -> None:
        original = getattr(error, "original_error", None) or error
        span.record_exception(original)
        span.set_attribute("error.type", type(original).__name__)
        if self._status is not None and self._status_code is not None:
            span.set_status(self._status(self._status_code.ERROR, str(original)))


def _requested_operation_name(context: Any) -> str | None:
    return getattr(context, "operation_name", None)


def _operation_details(context: Any) -> tuple[str, str | None]:
    operation = getattr(context, "operation", None)
    if operation is None:
        return "unknown", _requested_operation_name(context)
    name = operation.name.value if operation.name is not None else None
    return operation.operation, name


def _operation_details_from_info(info: Any) -> tuple[str, str | None]:
    operation = info.operation
    name = operation.name.value if operation.name is not None else None
    return operation.operation, name


__all__ = ["OpenTelemetryExtension"]
