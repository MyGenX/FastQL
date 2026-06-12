"""Dependency-free GraphQL-over-HTTP request handling."""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterable
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Mapping

from fastql.context import Context
from fastql.errors import GraphQLSyntaxError
from fastql.execution import ExecutionResult, execute, execute_incremental, subscribe
from fastql.integrations.multipart import (
    MultipartRequestError,
    parse_multipart_request,
)
from fastql.integrations.streaming import (
    MULTIPART_BOUNDARY,
    multipart_stream,
    single_result_stream,
    sse_stream,
)
from fastql.language import ast, parse
from fastql.playground import playground_html
from fastql.sdl import print_schema


JSON_MEDIA_TYPES = {"application/json", "application/graphql-response+json"}

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        args { name type { ...TypeRef } }
        type { ...TypeRef }
        isDeprecated
        deprecationReason
      }
      inputFields { name type { ...TypeRef } }
      interfaces { ...TypeRef }
      enumValues(includeDeprecated: true) {
        name
        isDeprecated
        deprecationReason
      }
      possibleTypes { ...TypeRef }
    }
    directives { name locations args { name type { ...TypeRef } } }
  }
}

fragment TypeRef on __Type {
  kind
  name
  ofType { kind name ofType { kind name ofType { kind name } } }
}
"""


def _normalize_path(path: str | None) -> str | None:
    if path is None:
        return None
    if not path:
        return "/"
    return path if path.startswith("/") else f"/{path}"


@dataclass(frozen=True)
class EndpointConfig:
    """Routes exposed by an integration."""

    path: str = "/graphql"
    graphiql: bool = False
    graphiql_path: str | None = None
    schema_path: str | None = None
    introspection_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _normalize_path(self.path))
        graphiql_path = self.graphiql_path
        if self.graphiql and graphiql_path is None:
            graphiql_path = self.path
        object.__setattr__(self, "graphiql_path", _normalize_path(graphiql_path))
        object.__setattr__(self, "schema_path", _normalize_path(self.schema_path))
        object.__setattr__(
            self, "introspection_path", _normalize_path(self.introspection_path)
        )

    @property
    def routes(self) -> tuple[str, ...]:
        values = (
            self.path,
            self.graphiql_path if self.graphiql else None,
            self.schema_path,
            self.introspection_path,
        )
        return tuple(dict.fromkeys(value for value in values if value is not None))


@dataclass
class HTTPRequest:
    """Framework-neutral request consumed by :class:`GraphQLHTTPHandler`."""

    method: str
    path: str
    headers: Mapping[str, str] = field(default_factory=dict)
    query_params: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""
    native_request: Any = None
    app: Any = None
    state: Any = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.method = self.method.upper()
        self.path = _normalize_path(self.path) or "/"
        if not isinstance(self.body, bytes):
            raise TypeError("HTTPRequest.body must be bytes.")
        self.headers = {str(key).lower(): str(value) for key, value in self.headers.items()}
        self.query_params = {
            str(key): str(value) for key, value in self.query_params.items()
        }

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)


@dataclass
class HTTPResponse:
    """Framework-neutral response returned by the shared handler."""

    status: int
    body: bytes | AsyncIterable[bytes] = b""
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def text(
        cls, status: int, body: str, content_type: str = "text/plain; charset=utf-8"
    ) -> "HTTPResponse":
        return cls(status, body.encode("utf-8"), {"content-type": content_type})

    @classmethod
    def json(
        cls,
        status: int,
        payload: Any,
        content_type: str = "application/json",
    ) -> "HTTPResponse":
        return cls(
            status,
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            {"content-type": content_type},
        )

    @classmethod
    def stream(
        cls,
        status: int,
        body: AsyncIterable[bytes],
        content_type: str,
    ) -> "HTTPResponse":
        return cls(status, body, {"content-type": content_type})

    @property
    def is_streaming(self) -> bool:
        return not isinstance(self.body, bytes)


@dataclass
class ResponseControl:
    """Request-scoped response changes available to context-aware code."""

    headers: dict[str, str] = field(default_factory=dict)

    def set_header(self, name: str, value: str) -> None:
        self.headers[str(name)] = str(value)


@dataclass
class HTTPContext(Context):
    """Portable web context carrying the native request and response controls."""

    request: Any
    app: Any = None
    state: Any = field(default_factory=dict)
    response: ResponseControl = field(default_factory=ResponseControl)


ContextFactory = Callable[[HTTPContext], Any | Awaitable[Any]]


class GraphQLHTTPHandler:
    """Shared GraphQL-over-HTTP implementation used by every adapter."""

    def __init__(
        self,
        schema: Any,
        *,
        path: str = "/graphql",
        context_factory: ContextFactory | Callable[[], Any] | None = None,
        root_value: Any = None,
        graphiql: bool = False,
        graphiql_path: str | None = None,
        schema_path: str | None = None,
        introspection_path: str | None = None,
        execution_options: Mapping[str, Any] | None = None,
        debug: bool = False,
        use_http_context: bool = True,
        allow_batching: bool = False,
        max_batch_size: int = 10,
        batching: bool | None = None,
    ) -> None:
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be a positive integer.")
        self.schema = schema
        self.endpoints = EndpointConfig(
            path=path,
            graphiql=graphiql,
            graphiql_path=graphiql_path,
            schema_path=schema_path,
            introspection_path=introspection_path,
        )
        self.context_factory = context_factory
        self.root_value = root_value
        self.execution_options = dict(execution_options or {})
        self.debug = debug
        self.use_http_context = use_http_context
        self.allow_batching = allow_batching if batching is None else batching
        self.max_batch_size = max_batch_size

    async def handle(self, request: HTTPRequest) -> HTTPResponse:
        if request.path not in self.endpoints.routes:
            return _error(404, f"Not found: {request.path}")
        if request.method == "OPTIONS":
            return HTTPResponse(204, headers={"allow": "GET, POST, OPTIONS"})
        if request.path == self.endpoints.schema_path:
            return self._schema_document(request)
        if request.path == self.endpoints.introspection_path:
            return await self._introspection_document(request)
        if (
            self.endpoints.graphiql
            and request.path == self.endpoints.graphiql_path
            and request.method == "GET"
            and not request.query_params.get("query")
        ):
            if self.endpoints.graphiql_path != self.endpoints.path or _accepts_html(request):
                return HTTPResponse.text(
                    200,
                    playground_html(self.endpoints.path),
                    "text/html; charset=utf-8",
                )
        if (
            request.path == self.endpoints.graphiql_path
            and self.endpoints.graphiql_path != self.endpoints.path
            and request.method != "GET"
        ):
            return _method_not_allowed("GET")
        if request.path != self.endpoints.path:
            return _error(404, f"Not found: {request.path}")
        return await self._graphql(request)

    def _schema_document(self, request: HTTPRequest) -> HTTPResponse:
        if request.method != "GET":
            return _method_not_allowed("GET")
        return HTTPResponse.text(
            200, print_schema(self.schema), "text/plain; charset=utf-8"
        )

    async def _introspection_document(self, request: HTTPRequest) -> HTTPResponse:
        if request.method != "GET":
            return _method_not_allowed("GET")
        result = await execute(self.schema, INTROSPECTION_QUERY)
        return HTTPResponse.json(200, result.formatted())

    async def _graphql(self, request: HTTPRequest) -> HTTPResponse:
        if request.method not in {"GET", "POST"}:
            return _method_not_allowed("GET, POST")
        payload, error = _request_payload(request)
        if error is not None:
            return error
        if isinstance(payload, list):
            return await self._batch(request, payload)
        return await self._single(request, payload)

    async def _batch(
        self, request: HTTPRequest, payloads: list[dict[str, Any]]
    ) -> HTTPResponse:
        if request.method != "POST":
            return _method_not_allowed("POST", "Batched operations require POST.")
        if not self.allow_batching:
            return _error(400, "Query batching is disabled.")
        if not payloads:
            return _error(400, "Batch request must contain at least one operation.")
        if len(payloads) > self.max_batch_size:
            return _error(
                400,
                f"Batch request exceeds the maximum size of {self.max_batch_size}.",
            )
        for payload in payloads:
            if (
                _operation_type(payload["query"], payload.get("operationName"))
                == "subscription"
            ):
                return _error(400, "Subscriptions cannot be executed in a batch.")

        try:
            context, root_value, base_context = await self.execution_values(request)
            results = []
            for payload in payloads:
                result = await execute(
                    self.schema,
                    payload["query"],
                    variable_values=payload.get("variables"),
                    context=context,
                    operation_name=payload.get("operationName"),
                    root_value=root_value,
                    **self.execution_options,
                )
                results.append(result.formatted())
            response = HTTPResponse.json(
                200,
                results,
                _response_media_type(request),
            )
            self._apply_context_headers(response, base_context, context)
            return response
        except Exception as error:  # adapter boundary must not leak internals
            message = str(error) if self.debug else "Internal server error."
            return _error(500, message)

    async def _single(
        self, request: HTTPRequest, payload: dict[str, Any]
    ) -> HTTPResponse:
        query = payload["query"]
        operation_name = payload.get("operationName")
        operation_type = _operation_type(query, operation_name)
        stream_media_type = _stream_media_type(request)
        is_streaming_subscription = (
            operation_type == "subscription" and stream_media_type is not None
        )
        is_incremental = (
            operation_type == "query"
            and stream_media_type is not None
            and _uses_incremental(query)
        )
        if (
            request.method == "GET"
            and operation_type != "query"
            and not is_streaming_subscription
        ):
            return _method_not_allowed(
                "POST", "Mutations and subscriptions require POST."
            )

        try:
            context, root_value, base_context = await self.execution_values(request)
            if is_incremental:
                results = execute_incremental(
                    self.schema,
                    query,
                    variable_values=payload.get("variables"),
                    context=context,
                    operation_name=operation_name,
                    root_value=root_value,
                    **self.execution_options,
                )
                if stream_media_type == "text/event-stream":
                    response = HTTPResponse.stream(
                        200,
                        sse_stream(results),
                        "text/event-stream; charset=utf-8",
                    )
                    response.headers["cache-control"] = "no-cache"
                else:
                    response = HTTPResponse.stream(
                        200,
                        multipart_stream(results),
                        f'multipart/mixed; boundary="{MULTIPART_BOUNDARY}"',
                    )
                self._apply_context_headers(response, base_context, context)
                return response
            if is_streaming_subscription:
                result_stream = await subscribe(
                    self.schema,
                    query,
                    variable_values=payload.get("variables"),
                    context=context,
                    operation_name=operation_name,
                    root_value=root_value,
                    **self.execution_options,
                )
                results = (
                    single_result_stream(result_stream)
                    if isinstance(result_stream, ExecutionResult)
                    else result_stream
                )
                if stream_media_type == "text/event-stream":
                    response = HTTPResponse.stream(
                        200,
                        sse_stream(results),
                        "text/event-stream; charset=utf-8",
                    )
                    response.headers["cache-control"] = "no-cache"
                else:
                    response = HTTPResponse.stream(
                        200,
                        multipart_stream(results),
                        f'multipart/mixed; boundary="{MULTIPART_BOUNDARY}"',
                    )
                self._apply_context_headers(response, base_context, context)
                return response
            result = await execute(
                self.schema,
                query,
                variable_values=payload.get("variables"),
                context=context,
                operation_name=operation_name,
                root_value=root_value,
                **self.execution_options,
            )
            response = HTTPResponse.json(
                200, result.formatted(), _response_media_type(request)
            )
            self._apply_context_headers(response, base_context, context)
            return response
        except Exception as error:  # adapter boundary must not leak internals
            message = str(error) if self.debug else "Internal server error."
            return _error(500, message)

    async def execution_values(
        self, request: HTTPRequest
    ) -> tuple[Any, Any, HTTPContext]:
        """Build the execution context and root value for any transport."""
        base_context = HTTPContext(
            request=request.native_request if request.native_request is not None else request,
            app=request.app,
            state=request.state,
        )
        if self.context_factory is None and not self.use_http_context:
            context = None
        else:
            context = await _make_context(self.context_factory, base_context)
        root_value = await _resolve_value(self.root_value, context)
        return context, root_value, base_context

    @staticmethod
    def _apply_context_headers(
        response: HTTPResponse, base_context: HTTPContext, context: Any
    ) -> None:
        response.headers.update(base_context.response.headers)
        if isinstance(context, HTTPContext) and context is not base_context:
            response.headers.update(context.response.headers)


async def _make_context(
    factory: ContextFactory | Callable[[], Any] | None, context: HTTPContext
) -> Any:
    if factory is None:
        return context
    try:
        parameters = inspect.signature(factory).parameters
    except (TypeError, ValueError):
        parameters = {"context": None}
    value = factory() if not parameters else factory(context)
    if inspect.isawaitable(value):
        value = await value
    return context if value is None else value


async def _resolve_value(value: Any, context: Any) -> Any:
    if not callable(value):
        return value
    try:
        parameters = inspect.signature(value).parameters
    except (TypeError, ValueError):
        parameters = {"context": None}
    resolved = value() if not parameters else value(context)
    if inspect.isawaitable(resolved):
        resolved = await resolved
    return resolved


def _request_payload(
    request: HTTPRequest,
) -> tuple[dict[str, Any] | list[dict[str, Any]] | None, HTTPResponse | None]:
    if request.method == "GET":
        raw: Any = dict(request.query_params)
        for key in ("variables", "extensions"):
            if key in raw:
                try:
                    raw[key] = json.loads(raw[key])
                except json.JSONDecodeError:
                    return None, _error(400, f"'{key}' is not valid JSON.")
    else:
        content_type = request.header("content-type")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type == "multipart/form-data":
            try:
                raw = parse_multipart_request(content_type, request.body)
            except MultipartRequestError as error:
                return None, _error(400, str(error))
        elif media_type in JSON_MEDIA_TYPES:
            try:
                raw = json.loads(request.body.decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None, _error(400, "Request body is not valid JSON.")
        else:
            return None, _error(415, "Unsupported media type.")
    if isinstance(raw, list):
        payloads = []
        for index, value in enumerate(raw):
            payload, error = _validate_payload(value, f"Batch item {index}")
            if error is not None:
                return None, error
            payloads.append(payload)
        return payloads, None
    return _validate_payload(raw, "Request body")


def _validate_payload(
    raw: Any, owner: str
) -> tuple[dict[str, Any] | None, HTTPResponse | None]:
    if not isinstance(raw, dict):
        return None, _error(400, f"{owner} must be a JSON object.")
    query = raw.get("query")
    if not isinstance(query, str) or not query.strip():
        return None, _error(400, f"{owner} has a missing or invalid 'query'.")
    variables = raw.get("variables")
    if variables is not None and not isinstance(variables, dict):
        return None, _error(400, f"{owner} 'variables' must be an object or null.")
    extensions = raw.get("extensions")
    if extensions is not None and not isinstance(extensions, dict):
        return None, _error(400, f"{owner} 'extensions' must be an object or null.")
    operation_name = raw.get("operationName")
    if operation_name is not None and not isinstance(operation_name, str):
        return None, _error(
            400, f"{owner} 'operationName' must be a string or null."
        )
    return {
        "query": query,
        "variables": variables,
        "operationName": operation_name,
        "extensions": extensions,
    }, None


def _is_non_query_operation(query: str, operation_name: str | None) -> bool:
    operation_type = _operation_type(query, operation_name)
    return operation_type is not None and operation_type != "query"


def _operation_type(query: str, operation_name: str | None) -> str | None:
    try:
        document = parse(query)
    except GraphQLSyntaxError:
        return False
    operations = [
        definition
        for definition in document.definitions
        if isinstance(definition, ast.OperationDefinitionNode)
    ]
    selected = None
    if operation_name is None and len(operations) == 1:
        selected = operations[0]
    elif operation_name is not None:
        selected = next(
            (
                operation
                for operation in operations
                if operation.name is not None
                and operation.name.value == operation_name
            ),
            None,
        )
    return selected.operation if selected is not None else None


def _accepts_html(request: HTTPRequest) -> bool:
    return "text/html" in request.header("accept").lower()


def _response_media_type(request: HTTPRequest) -> str:
    accepted = request.header("accept").lower()
    if "application/graphql-response+json" in accepted:
        return "application/graphql-response+json"
    return "application/json"


def _uses_incremental(query: str) -> bool:
    """True when the document applies ``@defer`` or ``@stream`` anywhere."""
    try:
        document = parse(query)
    except GraphQLSyntaxError:
        return False
    return _scan_incremental(document)


def _scan_incremental(node: Any) -> bool:
    if isinstance(node, ast.DirectiveNode):
        return node.name.value in ("defer", "stream")
    selections = getattr(node, "selections", None)
    if selections is not None and any(_scan_incremental(s) for s in selections):
        return True
    for attr in ("definitions", "directives"):
        items = getattr(node, attr, None)
        if items and any(_scan_incremental(item) for item in items):
            return True
    selection_set = getattr(node, "selection_set", None)
    if selection_set is not None and _scan_incremental(selection_set):
        return True
    return False


def _stream_media_type(request: HTTPRequest) -> str | None:
    accepted = request.header("accept").lower()
    if "text/event-stream" in accepted:
        return "text/event-stream"
    if "multipart/mixed" in accepted:
        return "multipart/mixed"
    return None


def _method_not_allowed(allow: str, message: str = "Method not allowed.") -> HTTPResponse:
    response = _error(405, message)
    response.headers["allow"] = allow
    return response


def _error(status: int, message: str) -> HTTPResponse:
    return HTTPResponse.json(status, {"errors": [{"message": message}]})


__all__ = [
    "ContextFactory",
    "EndpointConfig",
    "GraphQLHTTPHandler",
    "HTTPContext",
    "HTTPRequest",
    "HTTPResponse",
    "INTROSPECTION_QUERY",
    "JSON_MEDIA_TYPES",
    "ResponseControl",
]
