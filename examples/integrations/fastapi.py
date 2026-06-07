"""Run with: uvicorn examples.integrations.fastapi:app."""

from fastapi import FastAPI

from examples.hello import make_context, schema
from fastql.integrations.fastapi import create_fastapi_router

app = FastAPI()
app.include_router(
    create_fastapi_router(
        schema,
        context_factory=lambda _http: make_context(),
        graphiql=True,
    )
)
