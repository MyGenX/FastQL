"""CLI tests for the server-cli capability."""

import json

import pytest

from fastql.cli import _build_parser, _load_schema, main
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.types.schema import Schema


@pytest.fixture(autouse=True)
def clear_registries():
    # Keep examples.hello importable regardless of registry state left by other
    # test modules when this file runs first.
    default_registry.clear()
    default_dependencies.clear()


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


# -- export-schema ------------------------------------------------------------


def test_export_schema_parser_defaults():
    args = _build_parser().parse_args(["export-schema", "examples.hello:schema"])
    assert args.command == "export-schema"
    assert args.target == "examples.hello:schema"
    assert args.output is None
    assert args.format == "sdl"


def test_export_schema_sdl_to_stdout(capsys):
    main(["export-schema", "examples.hello:schema"])
    out = capsys.readouterr().out
    assert "type Query" in out
    assert "type User" in out


def test_export_schema_sdl_to_file(tmp_path):
    target = tmp_path / "schema.graphql"
    main(["export-schema", "examples.hello:schema", "--output", str(target)])
    text = target.read_text(encoding="utf-8")
    assert "type Query" in text
    assert text.endswith("\n")


def test_export_schema_json(capsys):
    main(["export-schema", "examples.hello:schema", "--format", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["__schema"]["queryType"]["name"] == "Query"


def test_export_schema_invalid_target_exits():
    with pytest.raises(SystemExit):
        main(["export-schema", "examples.hello:not_a_schema"])


def test_export_schema_non_schema_target_exits():
    # `make_context` is a callable, not a Schema.
    with pytest.raises(SystemExit):
        main(["export-schema", "examples.hello:make_context"])
