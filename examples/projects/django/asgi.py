"""ASGI entry point for the Django example.

Run:
    pip install -e ".[django]" uvicorn
    DJANGO_SETTINGS_MODULE=examples.projects.django.settings \\
        uvicorn examples.projects.django.asgi:application
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.projects.django.settings")

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
