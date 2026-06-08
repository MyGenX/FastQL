"""Django URL configuration exposing the FastQL endpoints."""

from __future__ import annotations

from examples.app import schema
from examples.projects._auth import build_context
from fastql.integrations.django import create_django_urlpatterns


def context_factory(http_context):
    request = http_context.request  # native Django HttpRequest
    return build_context(http_context, request.headers.get("X-User-Id"))


# csrf_exempt keeps the example simple; a real app would issue/verify CSRF tokens.
urlpatterns = create_django_urlpatterns(
    schema,
    context_factory=context_factory,
    graphiql=True,
    schema_path="/schema.graphql",
    csrf_exempt=True,
)
