"""Framework-neutral building blocks for FastQL HTTP integrations.

Framework adapters are intentionally not imported here. Import the adapter you
need from its module so a base ``fastql`` installation stays dependency-free.
"""

from fastql.integrations.asgi import ASGIRequest, GraphQLASGI
from fastql.integrations.http import (
    EndpointConfig,
    GraphQLHTTPHandler,
    HTTPContext,
    HTTPRequest,
    HTTPResponse,
    ResponseControl,
)
from fastql.integrations.streaming import (
    MULTIPART_BOUNDARY,
    multipart_stream,
    sse_stream,
)
from fastql.integrations.websocket import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GraphQLTransportWSHandler,
)

__all__ = [
    "ASGIRequest",
    "EndpointConfig",
    "GraphQLASGI",
    "GraphQLHTTPHandler",
    "GraphQLTransportWSHandler",
    "GRAPHQL_TRANSPORT_WS_PROTOCOL",
    "HTTPContext",
    "HTTPRequest",
    "HTTPResponse",
    "MULTIPART_BOUNDARY",
    "ResponseControl",
    "multipart_stream",
    "sse_stream",
]
