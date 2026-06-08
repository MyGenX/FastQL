# FastQL × Django

Mounts [`examples.app.schema`](../../app) on Django via `create_django_urlpatterns`, served
through Django's async-capable view over ASGI. This folder is a minimal but **runnable**
project (`settings.py` + `urls.py` + `asgi.py`).

```bash
pip install -e ".[django]" uvicorn
DJANGO_SETTINGS_MODULE=examples.projects.django.settings \
    uvicorn examples.projects.django.asgi:application
```

| Route | Description |
| --- | --- |
| `GET /graphql` | GraphiQL IDE |
| `POST /graphql` | GraphQL endpoint |
| `GET /schema.graphql` | SDL |

```bash
curl -s http://127.0.0.1:8000/graphql -i \
     -H 'content-type: application/json' -H 'X-User-Id: 1' \
     -d '{"query":"{ me { name role } }"}'
```

Per-request auth/customization is shared in [`examples/projects/_auth.py`](../_auth.py). The
example sets `csrf_exempt=True` for brevity; a real app would verify CSRF tokens instead.

**Subscriptions** are not served over HTTP yet — see
[`examples/app/demo.py`](../../app/demo.py).
