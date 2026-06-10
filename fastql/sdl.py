"""Render a built :class:`~fastql.types.schema.Schema` to GraphQL SDL text.

Used by the dev server's ``/schema.graphql`` endpoint and useful on its own for
inspecting a schema. Built-in scalars and introspection types (``__``-prefixed)
are omitted; deprecations are rendered as ``@deprecated(reason: ...)``.
"""

from __future__ import annotations

import json
from enum import Enum as PythonEnum
from typing import Any

from fastql.types import (
    EnumType,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    UnionType,
)
from fastql.types.wrappers import ListType, NonNull

_BUILTIN_SCALARS = {"Int", "Float", "String", "Boolean", "ID"}


def print_schema(schema: Any) -> str:
    """Return the SDL representation of ``schema``."""
    blocks = []
    for name in sorted(schema.type_map):
        if name.startswith("__") or name in _BUILTIN_SCALARS:
            continue
        rendered = _render_type(schema.type_map[name])
        if rendered:
            blocks.append(rendered)
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _render_type(type_: Any) -> str:
    if isinstance(type_, ObjectType):
        return _render_fields_block("type", type_, type_.interfaces)
    if isinstance(type_, InterfaceType):
        return _render_fields_block("interface", type_, [])
    if isinstance(type_, InputObjectType):
        return _render_input_block(type_)
    if isinstance(type_, EnumType):
        return _render_enum(type_)
    if isinstance(type_, UnionType):
        members = " | ".join(member.name for member in type_.types)
        return f"union {type_.name} = {members}"
    if isinstance(type_, ScalarType):
        return f"scalar {type_.name}"
    return ""


def _render_fields_block(keyword: str, type_: Any, interfaces: list) -> str:
    impl = ""
    if interfaces:
        impl = " implements " + " & ".join(i.name for i in interfaces)
    directives = _render_directives(getattr(type_, "directives", []))
    lines = [f"{keyword} {type_.name}{impl}{directives} {{"]
    for name, field in type_.fields.items():
        if name.startswith("__"):
            continue
        lines.append("  " + _render_field(name, field))
    lines.append("}")
    return "\n".join(lines)


def _render_field(name: str, field: Any) -> str:
    args = ""
    if field.args:
        args = "(" + ", ".join(
            _render_input_value(n, a) for n, a in field.args.items()
        ) + ")"
    out = f"{name}{args}: {_render_type_ref(field.type)}"
    if field.deprecation_reason:
        out += f" @deprecated(reason: {json.dumps(field.deprecation_reason)})"
    has_external_directive = any(
        directive.name == "external"
        for directive in getattr(field, "directives", [])
    )
    if getattr(field, "external", False) and not has_external_directive:
        out += " @external"
    out += _render_directives(getattr(field, "directives", []))
    return out


def _render_input_block(type_: InputObjectType) -> str:
    directives = _render_directives(getattr(type_, "directives", []))
    lines = [f"input {type_.name}{directives} {{"]
    for name, input_field in type_.fields.items():
        lines.append("  " + _render_input_value(name, input_field))
    lines.append("}")
    return "\n".join(lines)


def _render_input_value(name: str, value: Any) -> str:
    out = f"{name}: {_render_type_ref(value.type)}"
    default = getattr(value, "default_value", None)
    if default is not None:
        out += f" = {_render_value(default)}"
    if getattr(value, "deprecation_reason", None):
        out += f" @deprecated(reason: {json.dumps(value.deprecation_reason)})"
    out += _render_directives(getattr(value, "directives", []))
    return out


def _render_enum(type_: EnumType) -> str:
    directives = _render_directives(getattr(type_, "directives", []))
    lines = [f"enum {type_.name}{directives} {{"]
    for name, enum_value in type_.values.items():
        line = "  " + name
        if enum_value.deprecation_reason:
            line += f" @deprecated(reason: {json.dumps(enum_value.deprecation_reason)})"
        lines.append(line)
    lines.append("}")
    return "\n".join(lines)


def _render_type_ref(type_ref: Any) -> str:
    if isinstance(type_ref, NonNull):
        return _render_type_ref(type_ref.of_type) + "!"
    if isinstance(type_ref, ListType):
        return "[" + _render_type_ref(type_ref.of_type) + "]"
    return getattr(type_ref, "name", str(type_ref))


def _render_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, PythonEnum):
        return value.name
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_render_value(v) for v in value) + "]"
    return json.dumps(str(value))


def _render_directives(directives: list[Any]) -> str:
    rendered = []
    for directive in directives:
        args = getattr(directive, "arguments", {})
        suffix = ""
        if args:
            suffix = "(" + ", ".join(
                f"{name}: {_render_value(value)}" for name, value in args.items()
            ) + ")"
        rendered.append(f" @{directive.name}{suffix}")
    return "".join(rendered)


__all__ = ["print_schema"]
