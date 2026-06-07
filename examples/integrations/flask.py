"""Run with: flask --app examples.integrations.flask run."""

from flask import Flask

from examples.hello import make_context, schema
from fastql.integrations.flask import create_flask_blueprint

app = Flask(__name__)
app.register_blueprint(
    create_flask_blueprint(
        schema,
        context_factory=lambda _http: make_context(),
        graphiql=True,
    )
)
