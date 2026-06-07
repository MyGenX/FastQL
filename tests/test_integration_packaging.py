"""Packaging and optional-import boundaries for framework integrations."""

from __future__ import annotations

import ast
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_base_distribution_has_no_runtime_dependencies():
    assert PYPROJECT["project"]["dependencies"] == []


def test_every_adapter_has_an_independent_extra_and_all_is_the_union():
    extras = PYPROJECT["project"]["optional-dependencies"]
    assert set(("asgi", "starlette", "fastapi", "flask", "django", "all")) <= set(extras)
    assert extras["asgi"] == []
    for name in ("starlette", "fastapi", "flask", "django"):
        own = " ".join(extras[name]).lower()
        assert name in own
        for unrelated in {"starlette", "fastapi", "flask", "django"} - {name}:
            assert unrelated not in own
    expected = set().union(*(extras[name] for name in ("starlette", "fastapi", "flask", "django")))
    assert set(extras["all"]) == expected


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
    for name in ("starlette", "fastapi", "flask", "django"):
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
        assert any(f"fastql[{name}]" in message for message in messages)


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
    wheel = next(tmp_path.glob("fastql-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode()
    assert "fastql/integrations/http.py" in names
    assert "fastql/integrations/django.py" in names
    for extra in ("asgi", "starlette", "fastapi", "flask", "django", "all"):
        assert f"Provides-Extra: {extra}" in metadata
