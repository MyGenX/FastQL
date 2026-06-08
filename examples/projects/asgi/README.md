# FastQL × raw ASGI

Mounts [`examples.app.schema`](../../app) on the dependency-free `GraphQLASGI` adapter that
ships in the base install — no framework extra required.

```bash
pip install uvicorn
uvicorn examples.projects.asgi.app:application
```

| Route | Description |
| --- | --- |
| `GET /graphql` | GraphiQL IDE |
| `POST /graphql` | GraphQL endpoint |
| `GET /schema.graphql` | SDL |

```bash
curl -s http://127.0.0.1:8000/graphql -i \
     -H 'content-type: application/json' -H 'X-User-Id: 2' \
     -d '{"query":"{ me { name role } }"}'
```

Per-request auth/customization is shared in [`examples/projects/_auth.py`](../_auth.py);
here the only framework-specific part is decoding headers from the raw ASGI scope.

**Subscriptions** are not served over HTTP yet — see
[`examples/app/demo.py`](../../app/demo.py).
