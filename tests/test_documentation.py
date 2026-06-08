"""Repository-level checks for the Mintlify documentation project."""

from __future__ import annotations

import json
import ast
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs"
FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
LOCAL_LINK = re.compile(r"\]\((/[^)#?]+)(?:#[^)]+)?\)|href=\"(/[^\"#?]+)")
SPEC_LINK = re.compile(
    r"https://github\.com/fastql/fastql/blob/main/openspec/specs/([^/]+)/spec\.md"
)


def _navigation_pages(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "pages" and isinstance(child, list):
                for page in child:
                    if isinstance(page, str):
                        yield page
                    else:
                        yield from _navigation_pages(page)
            else:
                yield from _navigation_pages(child)
    elif isinstance(value, list):
        for child in value:
            yield from _navigation_pages(child)


def _page_path(route: str) -> Path:
    return DOCS / f"{route}.mdx"


def test_docs_config_and_navigation_are_complete():
    config = json.loads((DOCS / "docs.json").read_text())
    assert config["$schema"] == "https://mintlify.com/docs.json"
    assert config["theme"] == "mint"

    pages = list(_navigation_pages(config["navigation"]))
    assert pages
    assert len(pages) == len(set(pages)), "navigation routes must be unique"

    discovered = {
        page.relative_to(DOCS).with_suffix("").as_posix()
        for page in DOCS.rglob("*.mdx")
    }
    assert set(pages) == discovered


def test_every_page_has_required_frontmatter_and_valid_local_links():
    for page in DOCS.rglob("*.mdx"):
        text = page.read_text()
        match = FRONTMATTER.match(text)
        assert match, f"missing frontmatter: {page.relative_to(ROOT)}"
        frontmatter = match.group("body")
        assert re.search(r"^title:\s*\S", frontmatter, re.MULTILINE)
        assert re.search(r"^description:\s*\S", frontmatter, re.MULTILINE)

        for groups in LOCAL_LINK.findall(text):
            route = next(group for group in groups if group)
            if route.startswith("/images/"):
                assert (DOCS / route.removeprefix("/")).is_file(), route
            else:
                assert _page_path(route.removeprefix("/")).is_file(), route


def test_capability_catalog_links_every_canonical_spec():
    catalog = (DOCS / "specifications/capability-catalog.mdx").read_text()
    linked_specs = set(SPEC_LINK.findall(catalog))
    canonical_specs = {
        path.parent.name for path in (ROOT / "openspec/specs").glob("*/spec.md")
    }
    assert linked_specs == canonical_specs


def test_documented_scope_keeps_unsupported_features_explicit():
    status = (DOCS / "start/project-status.mdx").read_text().lower()
    dev_server = (DOCS / "tooling/dev-server.mdx").read_text().lower()
    operations = (DOCS / "build/operations-and-schema.mdx").read_text().lower()

    assert "development convenience" in dev_server
    assert "no tls" in dev_server
    assert "production use" in dev_server
    assert "streaming subscription" in status
    assert "streaming subscription" in operations
    assert "federation" in status


def test_documentation_examples_execute_successfully():
    for snippet in ("quickstart.py", "first_schema.py"):
        result = subprocess.run(
            [sys.executable, str(DOCS / "snippets" / snippet)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr


def test_framework_integration_docs_and_examples_are_complete():
    config = json.loads((DOCS / "docs.json").read_text())
    pages = set(_navigation_pages(config["navigation"]))
    expected_pages = {
        "integrations/overview",
        "integrations/asgi-and-api-frameworks",
        "integrations/flask-and-django",
        "integrations/context",
        "integrations/http-contract",
    }
    assert expected_pages <= pages

    overview = (DOCS / "integrations" / "overview.mdx").read_text()
    for extra in ("asgi", "starlette", "fastapi", "flask", "django", "all"):
        assert f"fastql[{extra}]" in overview

    projects = ROOT / "examples" / "projects"
    # Each framework has a runnable mini-project that mounts the shared showcase schema.
    entrypoints = {
        "asgi": "asgi/app.py",
        "starlette": "starlette/app.py",
        "fastapi": "fastapi/app.py",
        "flask": "flask/app.py",
        "django": "django/urls.py",
    }
    for name, relative in entrypoints.items():
        source = (projects / relative).read_text()
        ast.parse(source)
        assert "schema" in source
        assert (projects / name / "README.md").exists()
