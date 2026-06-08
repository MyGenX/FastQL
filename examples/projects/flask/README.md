# FastQL × Flask

Mounts [`examples.app.schema`](../../app) on Flask via `create_flask_blueprint`. Flask is
synchronous; the adapter bridges to FastQL's async engine for you.

```bash
pip install -e ".[flask]"
flask --app examples.projects.flask.app run    # http://127.0.0.1:5000
```

| Route | Description |
| --- | --- |
| `GET /graphql` | GraphiQL IDE |
| `POST /graphql` | GraphQL endpoint |
| `GET /schema.graphql` | SDL |

```bash
curl -s http://127.0.0.1:5000/graphql -i \
     -H 'content-type: application/json' -H 'X-User-Id: 1' \
     -d '{"query":"{ me { name role } }"}'
```

Per-request auth/customization is shared in [`examples/projects/_auth.py`](../_auth.py).

**Subscriptions** are not served over HTTP yet — see
[`examples/app/demo.py`](../../app/demo.py).
