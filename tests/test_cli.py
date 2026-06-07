"""CLI tests for the server-cli capability."""

import pytest

from fastql.cli import _build_parser, _load_schema
from fastql.types.schema import Schema


def test_load_schema_by_colon_path():
    schema = _load_schema("examples.hello:schema")
    assert isinstance(schema, Schema)


def test_load_schema_by_dotted_path():
    schema = _load_schema("examples.hello.schema")
    assert isinstance(schema, Schema)


def test_load_schema_unknown_module_exits():
    with pytest.raises(SystemExit):
        _load_schema("does.not.exist:schema")


def test_load_schema_missing_attribute_exits():
    with pytest.raises(SystemExit):
        _load_schema("examples.hello:not_a_schema")


def test_parser_applies_host_and_port_overrides():
    args = _build_parser().parse_args(
        ["serve", "examples.hello:schema", "--host", "0.0.0.0", "--port", "8080"]
    )
    assert args.command == "serve"
    assert args.target == "examples.hello:schema"
    assert args.host == "0.0.0.0"
    assert args.port == 8080


def test_parser_defaults():
    args = _build_parser().parse_args(["serve", "examples.hello:schema"])
    assert args.host == "127.0.0.1"
    assert args.port == 7691
    assert args.context is None


def test_parser_accepts_context_target():
    args = _build_parser().parse_args(
        ["serve", "examples.hello:schema", "--context", "examples.hello:make_context"]
    )
    assert args.context == "examples.hello:make_context"
    # The context target resolves to a usable callable.
    factory = _load_schema(args.context)
    assert callable(factory)
