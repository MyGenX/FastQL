"""Run with an ASGI server: uvicorn examples.integrations.asgi:application."""

from examples.hello import make_context, schema
from fastql.integrations import GraphQLASGI

application = GraphQLASGI(
    schema,
    context_factory=lambda _http: make_context(),
    graphiql=True,
    schema_path="/schema.graphql",
)
