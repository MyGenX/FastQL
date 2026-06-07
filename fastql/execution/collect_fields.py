"""Field collection: flatten a selection set into the fields to resolve.

Honors fragment spreads and inline fragments (applying their type conditions to
the runtime object type) and the ``@skip`` / ``@include`` directives. Returns an
ordered mapping of response key (alias or field name) to the list of field nodes
that share that key, so duplicate selections merge in document order.
"""

from __future__ import annotations

from typing import Any

from fastql.language import ast
from fastql.types import InterfaceType, ObjectType, UnionType


def collect_fields(
    schema: Any,
    runtime_type: ObjectType,
    selection_set: ast.SelectionSetNode,
    variable_values: dict[str, Any],
    fragments: dict[str, ast.FragmentDefinitionNode],
) -> dict[str, list[ast.FieldNode]]:
    grouped: dict[str, list[ast.FieldNode]] = {}
    _collect(schema, runtime_type, selection_set, variable_values, fragments, grouped, set())
    return grouped


def _collect(schema, runtime_type, selection_set, variable_values, fragments, grouped, visited):
    for selection in selection_set.selections:
        if not _should_include(selection.directives, variable_values):
            continue
        if isinstance(selection, ast.FieldNode):
            key = selection.alias.value if selection.alias else selection.name.value
            grouped.setdefault(key, []).append(selection)
        elif isinstance(selection, ast.InlineFragmentNode):
            if not _condition_matches(
                schema, selection.type_condition, runtime_type
            ):
                continue
            _collect(
                schema, runtime_type, selection.selection_set,
                variable_values, fragments, grouped, visited,
            )
        elif isinstance(selection, ast.FragmentSpreadNode):
            name = selection.name.value
            if name in visited:
                continue
            visited.add(name)
            fragment = fragments.get(name)
            if fragment is None:
                continue
            if not _condition_matches(
                schema, fragment.type_condition, runtime_type
            ):
                continue
            _collect(
                schema, runtime_type, fragment.selection_set,
                variable_values, fragments, grouped, visited,
            )


def _condition_matches(schema, type_condition, runtime_type) -> bool:
    if type_condition is None:
        return True
    condition = schema.type_map.get(type_condition.name.value)
    if condition is None:
        return False
    return _fragment_applies(condition, runtime_type)


def _fragment_applies(condition, runtime_type) -> bool:
    if condition is runtime_type:
        return True
    if isinstance(condition, InterfaceType):
        interfaces = getattr(runtime_type, "interfaces", [])
        return condition in interfaces
    if isinstance(condition, UnionType):
        return runtime_type in condition.types
    return False


def _should_include(directives, variable_values) -> bool:
    if not directives:
        return True
    skip = _directive_if(directives, "skip", variable_values)
    if skip is True:
        return False
    include = _directive_if(directives, "include", variable_values)
    if include is False:
        return False
    return True


def _directive_if(directives, name, variable_values):
    for directive in directives:
        if directive.name.value != name:
            continue
        for argument in directive.arguments:
            if argument.name.value != "if":
                continue
            value = argument.value
            if isinstance(value, ast.VariableNode):
                return variable_values.get(value.name.value)
            if isinstance(value, ast.BooleanValueNode):
                return value.value
    return None
