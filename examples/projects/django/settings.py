"""Minimal Django settings so the example boots as a real (async) project.

A production project would have far more here; this is the smallest config that serves
the FastQL endpoints over ASGI.
"""

from __future__ import annotations

SECRET_KEY = "insecure-example-key-do-not-use-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

ROOT_URLCONF = "examples.projects.django.urls"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

DATABASES: dict = {}
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
