# FastQL × Starlette

Mounts [`examples.app.schema`](../../app) on Starlette via `create_starlette_router`.

```bash
pip install -e ".[starlette]" uvicorn
uvicorn examples.projects.starlette.app:app
```

| Route | Description |
| --- | --- |
| `GET /graphql` | GraphiQL IDE |
| `POST /graphql` | GraphQL endpoint |
| `GET /schema.graphql` | SDL |

```bash
curl -s http://127.0.0.1:8000/graphql -i \
     -H 'content-type: application/json' -H 'X-User-Id: 1' \
     -d '{"query":"{ me { name } posts(filter:{status:PUBLISHED}) { title } }"}'
```

Per-request auth/customization is shared in [`examples/projects/_auth.py`](../_auth.py).

**Subscriptions** are not served over HTTP yet — see
[`examples/app/demo.py`](../../app/demo.py).
