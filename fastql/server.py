"""A minimal, dependency-free async dev server for a FastQL schema.

Built on ``asyncio.start_server`` with a small hand-rolled HTTP/1.1 handler
(request line + headers + ``Content-Length`` body, ``Connection: close`` per
response). It is a developer convenience for trying a schema in the browser —
not a production server (no TLS, auth, keep-alive, or chunked transfer).

Routes:
    POST/GET  {path}            execute a GraphQL request -> {data, errors}
    GET       /                 the GraphiQL IDE
    GET       /schema.graphql   the schema as SDL (text/plain)
    GET       /schema.json      the schema's introspection result (JSON)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from fastql.integrations.http import GraphQLHTTPHandler, HTTPRequest

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7691
DEFAULT_PATH = "/graphql"

_REASONS = {
    200: "OK",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

@dataclass
class _Response:
    status: int
    body: str
    content_type: str = "application/json"


def _json(status: int, payload: Any) -> _Response:
    return _Response(status, json.dumps(payload))


def _error_response(status: int, message: str) -> _Response:
    return _json(status, {"errors": [{"message": message}]})


class _Dispatcher:
    """Routes a parsed request to a response. Independently unit-testable."""

    def __init__(
        self,
        schema: Any,
        path: str = DEFAULT_PATH,
        context_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.schema = schema
        self.path = path
        self.context_factory = context_factory
        self.handler = GraphQLHTTPHandler(
            schema,
            path=path,
            context_factory=context_factory,
            graphiql=True,
            graphiql_path="/",
            schema_path="/schema.graphql",
            introspection_path="/schema.json",
            use_http_context=False,
        )

    async def dispatch(
        self, method: str, path: str, params: dict[str, str], body: bytes
    ) -> _Response:
        headers = {"content-type": "application/json"} if method == "POST" else {}
        response = await self.handler.handle(
            HTTPRequest(
                method=method,
                path=path,
                headers=headers,
                query_params=params,
                body=body,
            )
        )
        return _Response(
            response.status,
            response.body.decode("utf-8"),
            response.headers.get("content-type", "application/json"),
        )


# --- socket layer ------------------------------------------------------------


async def _read_request(reader: asyncio.StreamReader):
    request_line = await reader.readline()
    if not request_line:
        return None
    try:
        method, target, _ = request_line.decode("latin-1").split(" ", 2)
    except ValueError:
        return None
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        key, _, value = line.decode("latin-1").partition(":")
        headers[key.strip().lower()] = value.strip()
    body = b""
    length = int(headers.get("content-length", "0") or "0")
    if length:
        body = await reader.readexactly(length)
    return method, target, headers, body


def _write_response(writer: asyncio.StreamWriter, response: _Response) -> None:
    body = response.body.encode("utf-8")
    head = f"HTTP/1.1 {response.status} {_REASONS.get(response.status, '')}\r\n"
    headers = {
        "Content-Type": response.content_type,
        "Content-Length": str(len(body)),
        "Connection": "close",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    head += "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
    writer.write(head.encode("latin-1") + body)


async def _handle(reader, writer, dispatcher: _Dispatcher) -> None:
    try:
        request = await _read_request(reader)
        if request is None:
            return
        method, target, _headers, body = request
        split = urlsplit(target)
        params = {k: v[0] for k, v in parse_qs(split.query).items()}
        response = await dispatcher.dispatch(method, split.path, params, body)
        _write_response(writer, response)
        await writer.drain()
    except Exception as error:  # never crash the connection loop
        try:
            _write_response(writer, _error_response(500, str(error)))
            await writer.drain()
        except Exception:
            pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def start_server(
    schema: Any,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    path: str = DEFAULT_PATH,
    context_factory: Callable[[], Any] | None = None,
) -> asyncio.AbstractServer:
    """Start the dev server and return the running ``asyncio`` server object."""
    dispatcher = _Dispatcher(schema, path, context_factory)

    async def handler(reader, writer):
        await _handle(reader, writer, dispatcher)

    return await asyncio.start_server(handler, host, port)


def _print_banner(host: str, port: int, path: str) -> None:
    base = f"http://{host}:{port}"
    print(
        f"FastQL dev server on {base}\n"
        f"  GraphiQL : {base}/\n"
        f"  GraphQL  : {base}{path}\n"
        f"  SDL      : {base}/schema.graphql\n"
        f"  Schema   : {base}/schema.json\n"
        "Press Ctrl-C to stop."
    )


def serve(
    schema: Any,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    path: str = DEFAULT_PATH,
    context: Any = None,
    context_factory: Callable[[], Any] | None = None,
) -> None:
    """Run the dev server (blocking) until interrupted with Ctrl-C.

    Supply ``context`` for a fixed per-request context value, or
    ``context_factory`` (a zero-arg callable, optionally async) to build a fresh
    context for each request. Resolvers receive it via their ``Context`` parameter.
    """
    if context_factory is None and context is not None:
        context_factory = lambda: context  # noqa: E731

    async def _run() -> None:
        server = await start_server(
            schema, host=host, port=port, path=path, context_factory=context_factory
        )
        bound = server.sockets[0].getsockname()
        _print_banner(bound[0], bound[1], path)
        async with server:
            await server.serve_forever()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nFastQL dev server stopped.")


__all__ = ["serve", "start_server"]
