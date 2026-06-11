"""Framework-neutral ``graphql-transport-ws`` protocol handler."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastql.execution import ExecutionResult, subscribe
from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest

GRAPHQL_TRANSPORT_WS_PROTOCOL = "graphql-transport-ws"

ReceiveMessage = Callable[[], Awaitable[Mapping[str, Any] | None]]
SendMessage = Callable[[dict[str, Any]], Awaitable[None]]


class GraphQLTransportWSHandler:
    """Drive FastQL subscriptions with the ``graphql-transport-ws`` protocol."""

    def __init__(self, http_handler: GraphQLHTTPHandler) -> None:
        self.http_handler = http_handler

    async def handle(
        self,
        receive: ReceiveMessage,
        send: SendMessage,
        *,
        request: HTTPRequest,
    ) -> None:
        operations: dict[str, asyncio.Task[None]] = {}
        send_lock = asyncio.Lock()
        acknowledged = False

        async def send_message(message: dict[str, Any]) -> None:
            async with send_lock:
                await send(message)

        try:
            while True:
                message = await receive()
                if message is None:
                    break
                message_type = message.get("type")
                if message_type == "connection_init":
                    if acknowledged:
                        await send_message(
                            {
                                "type": "error",
                                "payload": _protocol_error(
                                    "Too many initialization requests."
                                ),
                            }
                        )
                        continue
                    acknowledged = True
                    await send_message({"type": "connection_ack"})
                elif message_type == "ping":
                    response = {"type": "pong"}
                    if "payload" in message:
                        response["payload"] = message["payload"]
                    await send_message(response)
                elif message_type == "pong":
                    continue
                elif message_type == "subscribe":
                    operation_id = message.get("id")
                    if not acknowledged:
                        await send_message(
                            _operation_error(operation_id, "Connection has not been acknowledged.")
                        )
                        continue
                    if not isinstance(operation_id, str) or not operation_id:
                        await send_message(
                            _operation_error(
                                operation_id,
                                "Subscribe messages require a non-empty string id.",
                            )
                        )
                        continue
                    if operation_id in operations:
                        await send_message(
                            _operation_error(operation_id, "Subscriber id is already active.")
                        )
                        continue
                    payload = message.get("payload")
                    error = _payload_error(payload)
                    if error is not None:
                        await send_message(_operation_error(operation_id, error))
                        continue
                    task = asyncio.create_task(
                        self._run_operation(
                            operation_id,
                            payload,
                            request,
                            send_message,
                        )
                    )
                    operations[operation_id] = task
                    task.add_done_callback(
                        lambda _task, key=operation_id: operations.pop(key, None)
                    )
                elif message_type == "complete":
                    operation_id = message.get("id")
                    task = operations.pop(operation_id, None)
                    if task is not None:
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                else:
                    await send_message(
                        {"type": "error", "payload": _protocol_error("Unknown message type.")}
                    )
        finally:
            tasks = list(operations.values())
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_operation(
        self,
        operation_id: str,
        payload: Mapping[str, Any],
        request: HTTPRequest,
        send: SendMessage,
    ) -> None:
        stream = None
        try:
            context, root_value, _ = await self.http_handler.execution_values(request)
            stream = await subscribe(
                self.http_handler.schema,
                payload["query"],
                variable_values=payload.get("variables"),
                context=context,
                operation_name=payload.get("operationName"),
                root_value=root_value,
                **self.http_handler.execution_options,
            )
            if isinstance(stream, ExecutionResult):
                await send(
                    {
                        "id": operation_id,
                        "type": "error",
                        "payload": [error.formatted() for error in stream.errors],
                    }
                )
                return
            async for result in stream:
                await send(
                    {
                        "id": operation_id,
                        "type": "next",
                        "payload": result.formatted(),
                    }
                )
            await send({"id": operation_id, "type": "complete"})
        except asyncio.CancelledError:
            raise
        except Exception as error:
            message = str(error) if self.http_handler.debug else "Internal server error."
            await send(_operation_error(operation_id, message))
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()


def _payload_error(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return "Subscribe payload must be an object."
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        return "Subscribe payload requires a query string."
    variables = payload.get("variables")
    if variables is not None and not isinstance(variables, Mapping):
        return "Subscribe variables must be an object or null."
    operation_name = payload.get("operationName")
    if operation_name is not None and not isinstance(operation_name, str):
        return "Subscribe operationName must be a string or null."
    return None


def _operation_error(operation_id: Any, message: str) -> dict[str, Any]:
    response: dict[str, Any] = {
        "type": "error",
        "payload": _protocol_error(message),
    }
    if isinstance(operation_id, str):
        response["id"] = operation_id
    return response


def _protocol_error(message: str) -> list[dict[str, str]]:
    return [{"message": message}]


__all__ = ["GRAPHQL_TRANSPORT_WS_PROTOCOL", "GraphQLTransportWSHandler"]
