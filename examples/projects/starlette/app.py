"""FastQL on Starlette.

Run:
    pip install -e ".[starlette]" uvicorn
    uvicorn examples.projects.starlette.app:app
"""

from __future__ import annotations

from starlette.applications import Starlette

from examples.app import schema
from examples.projects._auth import build_context
from fastql.integrations.starlette import create_starlette_router


def context_factory(http_context):
    request = http_context.request  # native Starlette Request
    return build_context(http_context, request.headers.get("x-user-id"))


router = create_starlette_router(
    schema,
    context_factory=context_factory,
    graphiql=True,
    schema_path="/schema.graphql",
)
app = Starlette(routes=list(router.routes))
