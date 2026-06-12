"""Packaging and optional-import boundaries for framework integrations."""

from __future__ import annotations

import ast
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())
DIST_NAME = "mygenx-fastql"
DIST_FILENAME = "mygenx_fastql"


def test_base_distribution_has_no_runtime_dependencies():
    assert PYPROJECT["project"]["name"] == DIST_NAME
    assert PYPROJECT["project"]["dependencies"] == []


def test_runtime_version_matches_distribution_metadata():
    import fastql

    assert fastql.__version__ == PYPROJECT["project"]["version"]


#: Adapters whose extra pulls in exactly one framework, so their dependency
#: lists must be mutually exclusive. ``channels`` is excluded because it
#: intentionally also depends on Django (its HTTP side).
_STANDALONE_ADAPTERS = (
    "starlette",
    "fastapi",
    "flask",
    "django",
    "aiohttp",
    "sanic",
    "litestar",
    "quart",
)

#: Every adapter extra that should be folded into ``all``.
_ALL_ADAPTERS = _STANDALONE_ADAPTERS + ("channels",)


def test_every_adapter_has_an_independent_extra_and_all_is_the_union():
    extras = PYPROJECT["project"]["optional-dependencies"]
    assert set(("asgi", *_ALL_ADAPTERS, "all")) <= set(extras)
    assert extras["asgi"] == []
    for name in _STANDALONE_ADAPTERS:
        own = " ".join(extras[name]).lower()
        assert name in own
        for unrelated in set(_STANDALONE_ADAPTERS) - {name}:
            assert unrelated not in own
    expected = set().union(*(extras[name] for name in _ALL_ADAPTERS))
    assert set(extras["all"]) == expected


def test_opentelemetry_has_an_isolated_optional_extra():
    dependencies = " ".join(
        PYPROJECT["project"]["optional-dependencies"]["opentelemetry"]
    ).lower()
    assert "opentelemetry-api" in dependencies
    assert "opentelemetry-sdk" in dependencies


def test_core_and_framework_neutral_integrations_do_not_import_frameworks():
    code = """
import sys
import fastql
import fastql.integrations
blocked = {'starlette', 'fastapi', 'flask', 'django'}
loaded = blocked.intersection(name.split('.')[0] for name in sys.modules)
assert not loaded, loaded
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_missing_adapter_errors_name_the_installation_extra():
    for name in _ALL_ADAPTERS:
        source = (ROOT / "fastql" / "integrations" / f"{name}.py").read_text()
        tree = ast.parse(source)
        messages = [
            node.exc.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Raise)
            and isinstance(node.exc, ast.Call)
            and node.exc.args
            and isinstance(node.exc.args[0], ast.Constant)
            and isinstance(node.exc.args[0].value, str)
        ]
        assert any(f"{DIST_NAME}[{name}]" in message for message in messages)


def test_framework_modules_are_included_by_package_configuration():
    wheel_packages = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert wheel_packages == ["fastql"]
    for module in ("asgi", "starlette", "fastapi", "flask", "django", "http"):
        assert (ROOT / "fastql" / "integrations" / f"{module}.py").is_file()


def test_built_wheel_contains_adapters_and_optional_metadata(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    wheel = next(tmp_path.glob(f"{DIST_FILENAME}-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode()
    assert f"Name: {DIST_NAME}" in metadata
    package_dirs = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "fastql").rglob("*")
        if path.is_dir() and (path / "__init__.py").is_file()
    }
    package_dirs.add("fastql")
    for package_dir in package_dirs:
        assert f"{package_dir}/__init__.py" in names
    assert "fastql/integrations/http.py" in names
    assert "fastql/integrations/django.py" in names
    for extra in (
        "asgi",
        "starlette",
        "fastapi",
        "flask",
        "django",
        "opentelemetry",
        "all",
    ):
        assert f"Provides-Extra: {extra}" in metadata


def test_built_sdist_excludes_workspace_only_content(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    sdist = next(tmp_path.glob(f"{DIST_FILENAME}-*.tar.gz"))
    with tarfile.open(sdist) as archive:
        names = {Path(name).as_posix() for name in archive.getnames()}
    relative_names = {name.split("/", 1)[1] for name in names if "/" in name}
    assert "pyproject.toml" in relative_names
    assert "README.md" in relative_names
    assert "CHANGELOG.md" in relative_names
    assert "fastql/__init__.py" in relative_names
    assert not any("node_modules" in name for name in relative_names)
    assert not any(name.startswith(("tests/", "docs/", "openspec/")) for name in relative_names)
