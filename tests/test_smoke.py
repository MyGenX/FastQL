"""Smoke test: the package and its subpackages import cleanly."""

import importlib


def test_import_fastql():
    import fastql

    assert fastql.__version__


def test_import_subpackages():
    for name in (
        "fastql.language",
        "fastql.types",
        "fastql.decorators",
        "fastql.validation",
        "fastql.execution",
    ):
        assert importlib.import_module(name) is not None
