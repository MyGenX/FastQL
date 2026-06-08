"""FastQL on raw ASGI — no framework dependency at all.

``GraphQLASGI`` ships in the base install (no extra needed). Run with any ASGI server:
    pip install uvicorn
    uvicorn examples.projects.asgi.app:application
"""

from __future__ import annotations

from examples.app import schema
from examples.projects._auth import build_context
from fastql.integrations import GraphQLASGI


def context_factory(http_context):
    # The native request is an ASGIRequest; headers live in the raw scope.
    scope = http_context.request.scope
    headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }
    return build_context(http_context, headers.get("x-user-id"))


application = GraphQLASGI(
    schema,
    context_factory=context_factory,
    graphiql=True,
    schema_path="/schema.graphql",
)
