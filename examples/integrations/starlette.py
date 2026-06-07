"""Run with: uvicorn examples.integrations.starlette:app."""

from starlette.applications import Starlette

from examples.hello import make_context, schema
from fastql.integrations.starlette import create_starlette_router

router = create_starlette_router(
    schema,
    context_factory=lambda _http: make_context(),
    graphiql=True,
)
app = Starlette(routes=list(router.routes))
