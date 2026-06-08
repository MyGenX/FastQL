"""FastQL on FastAPI.

Run:
    pip install -e ".[fastapi]" uvicorn
    uvicorn examples.projects.fastapi.app:app

Then open http://127.0.0.1:8000/graphql for GraphiQL, or:
    curl -s http://127.0.0.1:8000/graphql -H 'content-type: application/json' \\
         -H 'X-User-Id: 1' -d '{"query":"{ me { name role } }"}' -i
"""

from __future__ import annotations

from fastapi import FastAPI

from examples.app import schema
from examples.projects._auth import build_context
from fastql.integrations.fastapi import create_fastapi_router


def context_factory(http_context):
    # http_context.request is the native Starlette/FastAPI Request.
    request = http_context.request
    return build_context(http_context, request.headers.get("x-user-id"))


app = FastAPI(title="FastQL × FastAPI")
app.include_router(
    create_fastapi_router(
        schema,
        context_factory=context_factory,
        graphiql=True,
        schema_path="/schema.graphql",
    )
)
