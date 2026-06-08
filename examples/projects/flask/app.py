"""FastQL on Flask (a sync framework; the adapter bridges the async engine).

Run:
    pip install -e ".[flask]"
    flask --app examples.projects.flask.app run
"""

from __future__ import annotations

from flask import Flask

from examples.app import schema
from examples.projects._auth import build_context
from fastql.integrations.flask import create_flask_blueprint


def context_factory(http_context):
    request = http_context.request  # native Flask request
    return build_context(http_context, request.headers.get("X-User-Id"))


app = Flask(__name__)
app.register_blueprint(
    create_flask_blueprint(
        schema,
        context_factory=context_factory,
        graphiql=True,
        schema_path="/schema.graphql",
    )
)
