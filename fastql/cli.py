"""Command-line entry point: ``python -m fastql serve module:attr``."""

from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any

from fastql.server import DEFAULT_HOST, DEFAULT_PORT, serve


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fastql", description="FastQL CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="Run the dev server for a schema.")
    serve_parser.add_argument(
        "target",
        help="Dotted path to the schema object, e.g. 'myapp.schema:schema'.",
    )
    serve_parser.add_argument("--host", default=DEFAULT_HOST)
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_parser.add_argument(
        "--context",
        default=None,
        help=(
            "Dotted path to a per-request context value or zero-arg factory, "
            "e.g. 'myapp:make_context'."
        ),
    )
    return parser


def _load_schema(target: str) -> Any:
    """Import and return the schema object named by a dotted ``module:attr`` path."""
    if ":" in target:
        module_name, attr = target.split(":", 1)
    else:
        module_name, _, attr = target.rpartition(".")
    if not module_name or not attr:
        raise SystemExit(
            f"Invalid target {target!r}; expected 'module:attr' or 'module.attr'."
        )
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise SystemExit(f"Could not import module {module_name!r}: {error}")
    try:
        return getattr(module, attr)
    except AttributeError:
        raise SystemExit(f"Module {module_name!r} has no attribute {attr!r}.")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        schema = _load_schema(args.target)
        context_factory = None
        if args.context:
            obj = _load_schema(args.context)
            context_factory = obj if callable(obj) else (lambda value=obj: value)
        serve(
            schema,
            host=args.host,
            port=args.port,
            context_factory=context_factory,
        )


if __name__ == "__main__":  # pragma: no cover
    main()
