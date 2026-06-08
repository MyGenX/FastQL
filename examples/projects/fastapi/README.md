# FastQL × FastAPI

Mounts [`examples.app.schema`](../../app) on FastAPI via `create_fastapi_router`.

```bash
pip install -e ".[fastapi]" uvicorn
uvicorn examples.projects.fastapi.app:app
```

| Route | Description |
| --- | --- |
| `GET /graphql` | GraphiQL IDE |
| `POST /graphql` | GraphQL endpoint |
| `GET /schema.graphql` | SDL |

```bash
# Authenticate as the admin (Ada) via the X-User-Id header; note the response header.
curl -s http://127.0.0.1:8000/graphql -i \
     -H 'content-type: application/json' -H 'X-User-Id: 1' \
     -d '{"query":"{ me { name role } users { name posts { title } } }"}'

# A mutation requires auth; admin-only fields require X-User-Id: 1.
curl -s http://127.0.0.1:8000/graphql \
     -H 'content-type: application/json' -H 'X-User-Id: 1' \
     -d '{"query":"mutation { createPost(input:{title:\"Hi\",body:\"...\"}) { id title author { name } } }"}'
```

The customization here — reading `X-User-Id` to build the context and setting an
`X-FastQL-User` response header — lives in the shared
[`examples/projects/_auth.py`](../_auth.py); only the header extraction is FastAPI-specific.

**Subscriptions** are not served over HTTP yet (no WebSocket/SSE transport). See
[`examples/app/demo.py`](../../app/demo.py) for subscriptions via the core `subscribe()` API.
