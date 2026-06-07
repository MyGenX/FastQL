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

__all__ = [
    "ASGIRequest",
    "EndpointConfig",
    "GraphQLASGI",
    "GraphQLHTTPHandler",
    "HTTPContext",
    "HTTPRequest",
    "HTTPResponse",
    "ResponseControl",
]
