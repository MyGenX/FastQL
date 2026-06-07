"""Include these patterns from a Django project's root URL configuration."""

from examples.hello import make_context, schema
from fastql.integrations.django import create_django_urlpatterns

urlpatterns = create_django_urlpatterns(
    schema,
    context_factory=lambda _http: make_context(),
    graphiql=True,
)
