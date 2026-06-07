"""Print an AST back to a GraphQL document string.

A small, deterministic printer used mainly for debugging and for rendering
parsed values. It is not a pretty-printer with configurable style — it produces
canonical, readable output.
"""

from __future__ import annotations

from fastql.language import ast


def print_ast(node: ast.Node) -> str:
    """Render an AST node (typically a ``DocumentNode``) to a string."""
    return _print(node)


def _print(node) -> str:
    if node is None:
        return ""
    method = _PRINTERS.get(type(node))
    if method is None:  # pragma: no cover - defensive
        raise TypeError(f"Cannot print AST node of type {type(node).__name__}.")
    return method(node)


def _block(items: list[str]) -> str:
    if not items:
        return ""
    inner = "\n".join(items)
    indented = "\n".join("  " + line for line in inner.split("\n"))
    return "{\n" + indented + "\n}"


def _join(items, sep: str = "") -> str:
    return sep.join(item for item in items if item)


def _wrap(start: str, value: str, end: str = "") -> str:
    return f"{start}{value}{end}" if value else ""


def _print_document(node: ast.DocumentNode) -> str:
    return "\n\n".join(_print(d) for d in node.definitions) + "\n"


def _print_operation(node: ast.OperationDefinitionNode) -> str:
    op = node.operation
    name = _print(node.name) if node.name else ""
    var_defs = _wrap(
        "(", ", ".join(_print(v) for v in node.variable_definitions), ")"
    )
    directives = _join((_print(d) for d in node.directives), " ")
    selection_set = _print(node.selection_set)
    # Use the query shorthand when there is nothing but the selection set.
    if op == "query" and not name and not var_defs and not directives:
        return selection_set
    prefix = _join([op, _join([name, var_defs])], " ")
    return _join([prefix, directives, selection_set], " ")


def _print_variable_definition(node: ast.VariableDefinitionNode) -> str:
    out = f"{_print(node.variable)}: {_print(node.type)}"
    if node.default_value is not None:
        out += f" = {_print(node.default_value)}"
    directives = _join((_print(d) for d in node.directives), " ")
    return _join([out, directives], " ")


def _print_fragment_definition(node: ast.FragmentDefinitionNode) -> str:
    name = _print(node.name)
    cond = _print(node.type_condition)
    directives = _join((_print(d) for d in node.directives), " ")
    head = f"fragment {name} on {cond}"
    return _join([head, directives, _print(node.selection_set)], " ")


def _print_selection_set(node: ast.SelectionSetNode) -> str:
    return _block([_print(s) for s in node.selections])


def _print_field(node: ast.FieldNode) -> str:
    alias = f"{_print(node.alias)}: " if node.alias else ""
    args = _wrap("(", ", ".join(_print(a) for a in node.arguments), ")")
    directives = _join((_print(d) for d in node.directives), " ")
    selection_set = _print(node.selection_set) if node.selection_set else ""
    head = f"{alias}{_print(node.name)}{args}"
    return _join([head, directives, selection_set], " ")


def _print_fragment_spread(node: ast.FragmentSpreadNode) -> str:
    directives = _join((_print(d) for d in node.directives), " ")
    return _join([f"...{_print(node.name)}", directives], " ")


def _print_inline_fragment(node: ast.InlineFragmentNode) -> str:
    cond = f"on {_print(node.type_condition)}" if node.type_condition else ""
    directives = _join((_print(d) for d in node.directives), " ")
    return _join(["...", cond, directives, _print(node.selection_set)], " ")


def _print_argument(node: ast.ArgumentNode) -> str:
    return f"{_print(node.name)}: {_print(node.value)}"


def _print_directive(node: ast.DirectiveNode) -> str:
    args = _wrap("(", ", ".join(_print(a) for a in node.arguments), ")")
    return f"@{_print(node.name)}{args}"


def _print_string(node: ast.StringValueNode) -> str:
    if node.block:
        return '"""\n' + node.value + '\n"""'
    return '"' + _escape_string(node.value) + '"'


def _escape_string(value: str) -> str:
    out = []
    for ch in value:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        else:
            out.append(ch)
    return "".join(out)


def _print_object_value(node: ast.ObjectValueNode) -> str:
    return "{" + ", ".join(_print(f) for f in node.fields) + "}"


def _print_list_value(node: ast.ListValueNode) -> str:
    return "[" + ", ".join(_print(v) for v in node.values) + "]"


_PRINTERS = {
    ast.NameNode: lambda n: n.value,
    ast.DocumentNode: _print_document,
    ast.OperationDefinitionNode: _print_operation,
    ast.VariableDefinitionNode: _print_variable_definition,
    ast.FragmentDefinitionNode: _print_fragment_definition,
    ast.SelectionSetNode: _print_selection_set,
    ast.FieldNode: _print_field,
    ast.FragmentSpreadNode: _print_fragment_spread,
    ast.InlineFragmentNode: _print_inline_fragment,
    ast.ArgumentNode: _print_argument,
    ast.DirectiveNode: _print_directive,
    ast.VariableNode: lambda n: f"${_print(n.name)}",
    ast.IntValueNode: lambda n: n.value,
    ast.FloatValueNode: lambda n: n.value,
    ast.StringValueNode: _print_string,
    ast.BooleanValueNode: lambda n: "true" if n.value else "false",
    ast.NullValueNode: lambda n: "null",
    ast.EnumValueNode: lambda n: n.value,
    ast.ListValueNode: _print_list_value,
    ast.ObjectValueNode: _print_object_value,
    ast.ObjectFieldNode: lambda n: f"{_print(n.name)}: {_print(n.value)}",
    ast.NamedTypeNode: lambda n: _print(n.name),
    ast.ListTypeNode: lambda n: f"[{_print(n.type)}]",
    ast.NonNullTypeNode: lambda n: f"{_print(n.type)}!",
}
