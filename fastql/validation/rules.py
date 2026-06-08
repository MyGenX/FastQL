"""Validate a parsed operation against a built schema.

A pragmatic, growable subset of the GraphQL validation rules covering the
must-have checks: selected fields exist on their parent type, arguments are
defined (and literal scalar values coerce), fragment targets exist and are
composite, and every variable used is defined by its operation. ``validate``
returns a list of located errors (empty when the document is valid); it never
raises for ordinary validation failures.
"""

from __future__ import annotations

from typing import Any

from fastql.errors import ValidationError
from fastql.language import ast
from fastql.types import (
    EnumType,
    InterfaceType,
    ObjectType,
    ScalarType,
    UnionType,
)
from fastql.types.scalars import ScalarCoercionError
from fastql.types.wrappers import ListType, NonNull

_INTROSPECTION_ROOT_FIELDS = {"__schema", "__type"}
_COMPOSITE = (ObjectType, InterfaceType, UnionType)
_LEAF = (ScalarType, EnumType)


def validate(schema: Any, document: ast.DocumentNode) -> list[ValidationError]:
    """Return validation errors for ``document`` against ``schema``."""
    return _Validator(schema, document).run()


class _Validator:
    def __init__(self, schema: Any, document: ast.DocumentNode) -> None:
        self.schema = schema
        self.document = document
        self.errors: list[ValidationError] = []
        self.fragments: dict[str, ast.FragmentDefinitionNode] = {
            d.name.value: d
            for d in document.definitions
            if isinstance(d, ast.FragmentDefinitionNode)
        }

    def run(self) -> list[ValidationError]:
        self._check_lone_anonymous_operation()
        self._check_unique_operation_names()
        self._check_no_fragment_cycles()
        self._validate_directives()
        for definition in self.document.definitions:
            if isinstance(definition, ast.OperationDefinitionNode):
                self._validate_operation(definition)
            elif isinstance(definition, ast.FragmentDefinitionNode):
                self._validate_fragment_definition(definition)
        return self.errors

    # -- document-level rules -------------------------------------------------

    def _operations(self) -> list[ast.OperationDefinitionNode]:
        return [
            d
            for d in self.document.definitions
            if isinstance(d, ast.OperationDefinitionNode)
        ]

    def _check_lone_anonymous_operation(self) -> None:
        operations = self._operations()
        if len(operations) <= 1:
            return
        for operation in operations:
            if operation.name is None:
                self._error(
                    "This anonymous operation must be the only defined operation.",
                    operation,
                )

    def _check_unique_operation_names(self) -> None:
        seen: set[str] = set()
        for operation in self._operations():
            if operation.name is None:
                continue
            name = operation.name.value
            if name in seen:
                self._error(
                    f"There can be only one operation named {name!r}.", operation
                )
            seen.add(name)

    def _check_no_fragment_cycles(self) -> None:
        for name in self.fragments:
            self._detect_fragment_cycle(name, [name], set())

    def _detect_fragment_cycle(
        self, name: str, path: list[str], reported: set[str]
    ) -> None:
        fragment = self.fragments.get(name)
        if fragment is None:
            return
        for spread in self._spreads_in(fragment.selection_set):
            target = spread.name.value
            if target in path:
                key = "->".join(sorted({*path, target}))
                if key not in reported:
                    reported.add(key)
                    self._error(
                        f"Cannot spread fragment {target!r} within itself"
                        + (
                            f" via {' -> '.join(path[path.index(target) + 1:])}."
                            if path[-1] != target
                            else "."
                        ),
                        spread,
                    )
                continue
            self._detect_fragment_cycle(target, [*path, target], reported)

    def _spreads_in(
        self, selection_set: ast.SelectionSetNode
    ) -> list[ast.FragmentSpreadNode]:
        spreads: list[ast.FragmentSpreadNode] = []
        for selection in selection_set.selections:
            if isinstance(selection, ast.FragmentSpreadNode):
                spreads.append(selection)
            elif isinstance(selection, ast.FieldNode):
                if selection.selection_set is not None:
                    spreads.extend(self._spreads_in(selection.selection_set))
            elif isinstance(selection, ast.InlineFragmentNode):
                spreads.extend(self._spreads_in(selection.selection_set))
        return spreads

    # -- directives -----------------------------------------------------------

    def _validate_directives(self) -> None:
        for definition in self.document.definitions:
            if isinstance(definition, ast.OperationDefinitionNode):
                location = {
                    "query": "QUERY",
                    "mutation": "MUTATION",
                    "subscription": "SUBSCRIPTION",
                }[definition.operation]
                self._check_directives(definition.directives, location)
                for variable in definition.variable_definitions:
                    self._check_directives(
                        variable.directives, "VARIABLE_DEFINITION"
                    )
                self._check_directives_in_selection_set(definition.selection_set)
            elif isinstance(definition, ast.FragmentDefinitionNode):
                self._check_directives(definition.directives, "FRAGMENT_DEFINITION")
                self._check_directives_in_selection_set(definition.selection_set)

    def _check_directives_in_selection_set(
        self, selection_set: ast.SelectionSetNode
    ) -> None:
        for selection in selection_set.selections:
            if isinstance(selection, ast.FieldNode):
                self._check_directives(selection.directives, "FIELD")
                if selection.selection_set is not None:
                    self._check_directives_in_selection_set(selection.selection_set)
            elif isinstance(selection, ast.FragmentSpreadNode):
                self._check_directives(selection.directives, "FRAGMENT_SPREAD")
            elif isinstance(selection, ast.InlineFragmentNode):
                self._check_directives(selection.directives, "INLINE_FRAGMENT")
                self._check_directives_in_selection_set(selection.selection_set)

    def _check_directives(
        self, directives: list[ast.DirectiveNode], location: str
    ) -> None:
        for directive in directives:
            definition = self.schema.directives.get(directive.name.value)
            if definition is None:
                self._error(
                    f"Unknown directive '@{directive.name.value}'.", directive
                )
                continue
            if location not in definition.locations:
                self._error(
                    f"Directive '@{directive.name.value}' may not be used on "
                    f"{location}.",
                    directive,
                )
            self._check_unique_arguments(
                directive.arguments, f"@{directive.name.value}", directive
            )

    # -- error helper ---------------------------------------------------------

    def _error(self, message: str, node: ast.Node | None) -> None:
        locations = []
        loc = getattr(node, "loc", None)
        if loc is not None:
            from fastql.language.source import get_location

            locations = [get_location(loc.source, loc.start)]
        self.errors.append(ValidationError(message, locations=locations))

    # -- operations -----------------------------------------------------------

    def _validate_operation(self, operation: ast.OperationDefinitionNode) -> None:
        root = self._root_type(operation.operation)
        if root is None:
            self._error(
                f"Schema is not configured to execute {operation.operation} operations.",
                operation,
            )
            return
        if operation.operation == "subscription":
            self._validate_single_root_field(operation)
        self._check_unique_variable_names(operation)
        self._validate_selection_set(operation.selection_set, root)
        self._validate_field_merging(operation.selection_set, root)
        self._check_variables(operation)

    def _check_unique_variable_names(
        self, operation: ast.OperationDefinitionNode
    ) -> None:
        seen: set[str] = set()
        for definition in operation.variable_definitions:
            name = definition.variable.name.value
            if name in seen:
                self._error(
                    f"There can be only one variable named '${name}'.",
                    definition,
                )
            seen.add(name)

    def _validate_single_root_field(
        self, operation: ast.OperationDefinitionNode
    ) -> None:
        fields = self._root_fields(operation.selection_set, set())
        keys = {
            (f.alias.value if f.alias else f.name.value) for f in fields
        }
        if len(keys) != 1:
            self._error(
                "Subscription operations must have exactly one root field.",
                operation,
            )
            return
        only = fields[0]
        if only.name.value.startswith("__"):
            self._error(
                "Subscription operations must not select an introspection field "
                "as the root field.",
                only,
            )

    def _root_fields(
        self, selection_set: ast.SelectionSetNode, seen: set[str]
    ) -> list[ast.FieldNode]:
        found: list[ast.FieldNode] = []
        for selection in selection_set.selections:
            if isinstance(selection, ast.FieldNode):
                found.append(selection)
            elif isinstance(selection, ast.InlineFragmentNode):
                found.extend(self._root_fields(selection.selection_set, seen))
            elif isinstance(selection, ast.FragmentSpreadNode):
                name = selection.name.value
                if name in self.fragments and name not in seen:
                    seen.add(name)
                    found.extend(
                        self._root_fields(
                            self.fragments[name].selection_set, seen
                        )
                    )
        return found

    def _root_type(self, operation: str) -> Any:
        if operation == "query":
            return self.schema.query
        if operation == "mutation":
            return self.schema.mutation
        if operation == "subscription":
            return self.schema.subscription
        return None

    def _validate_fragment_definition(
        self, fragment: ast.FragmentDefinitionNode
    ) -> None:
        type_name = fragment.type_condition.name.value
        condition = self.schema.type_map.get(type_name)
        if condition is None:
            self._error(
                f"Unknown type {type_name!r} for fragment {fragment.name.value!r}.",
                fragment.type_condition,
            )
            return
        if not isinstance(condition, _COMPOSITE):
            self._error(
                f"Fragment {fragment.name.value!r} cannot condition on non-composite "
                f"type {type_name!r}.",
                fragment.type_condition,
            )
            return
        self._validate_selection_set(fragment.selection_set, condition)

    # -- selection sets -------------------------------------------------------

    def _validate_selection_set(
        self, selection_set: ast.SelectionSetNode, parent_type: Any
    ) -> None:
        for selection in selection_set.selections:
            if isinstance(selection, ast.FieldNode):
                self._validate_field(selection, parent_type)
            elif isinstance(selection, ast.FragmentSpreadNode):
                self._validate_fragment_spread(selection, parent_type)
            elif isinstance(selection, ast.InlineFragmentNode):
                self._validate_inline_fragment(selection, parent_type)

    def _validate_field(self, field: ast.FieldNode, parent_type: Any) -> None:
        name = field.name.value

        if name == "__typename":
            return  # valid on any composite type, takes no arguments or subfields

        if name in _INTROSPECTION_ROOT_FIELDS and parent_type is self.schema.query:
            return  # introspection meta-fields are wired in by the executor

        if isinstance(parent_type, UnionType):
            self._error(
                f"Cannot query field {name!r} directly on union type "
                f"{parent_type.name!r}; use a fragment.",
                field,
            )
            return

        field_def = None
        if isinstance(parent_type, (ObjectType, InterfaceType)):
            field_def = parent_type.fields.get(name)
        if field_def is None:
            self._error(
                f"Cannot query field {name!r} on type {parent_type.name!r}.",
                field,
            )
            return

        self._validate_arguments(field, field_def)

        named = _named_type(field_def.type)
        if isinstance(named, _LEAF):
            if field.selection_set is not None:
                self._error(
                    f"Field {name!r} must not have a selection of subfields.",
                    field,
                )
        elif isinstance(named, _COMPOSITE):
            if field.selection_set is None:
                self._error(
                    f"Field {name!r} of type {named.name!r} must have a selection "
                    f"of subfields.",
                    field,
                )
            else:
                self._validate_selection_set(field.selection_set, named)

    def _validate_arguments(self, field: ast.FieldNode, field_def: Any) -> None:
        self._check_unique_arguments(
            field.arguments, f"field {field.name.value!r}", field
        )
        for argument in field.arguments:
            arg_name = argument.name.value
            arg_def = field_def.args.get(arg_name)
            if arg_def is None:
                self._error(
                    f"Unknown argument {arg_name!r} on field {field.name.value!r}.",
                    argument,
                )
                continue
            self._check_argument_value(argument, arg_def)

    def _check_unique_arguments(
        self, arguments: list[ast.ArgumentNode], owner: str, node: ast.Node
    ) -> None:
        seen: set[str] = set()
        for argument in arguments:
            name = argument.name.value
            if name in seen:
                self._error(
                    f"There can be only one argument named {name!r} on {owner}.",
                    argument,
                )
            seen.add(name)

    def _check_argument_value(self, argument: ast.ArgumentNode, arg_def: Any) -> None:
        value = argument.value
        self._check_input_field_uniqueness(value)
        if isinstance(value, (ast.VariableNode, ast.NullValueNode)):
            return
        named = _named_type(arg_def.type)
        if isinstance(named, ScalarType):
            try:
                named.parse_literal(value)
            except ScalarCoercionError:
                self._error(
                    f"Invalid value for argument {argument.name.value!r} of type "
                    f"{named.name!r}.",
                    argument,
                )

    def _check_input_field_uniqueness(self, value: ast.ValueNode) -> None:
        if isinstance(value, ast.ObjectValueNode):
            seen: set[str] = set()
            for field in value.fields:
                name = field.name.value
                if name in seen:
                    self._error(
                        f"There can be only one input field named {name!r}.",
                        field,
                    )
                seen.add(name)
                self._check_input_field_uniqueness(field.value)
        elif isinstance(value, ast.ListValueNode):
            for item in value.values:
                self._check_input_field_uniqueness(item)

    # -- fragments ------------------------------------------------------------

    def _validate_fragment_spread(
        self, spread: ast.FragmentSpreadNode, parent_type: Any
    ) -> None:
        fragment = self.fragments.get(spread.name.value)
        if fragment is None:
            self._error(f"Unknown fragment {spread.name.value!r}.", spread)
            return
        condition = self.schema.type_map.get(fragment.type_condition.name.value)
        if condition is None:
            return  # reported by the fragment definition's own validation
        if not self._types_overlap(parent_type, condition):
            self._error(
                f"Fragment {spread.name.value!r} cannot be spread here as objects "
                f"of type {_typename(condition)!r} can never be of type "
                f"{_typename(parent_type)!r}.",
                spread,
            )

    def _validate_inline_fragment(
        self, inline: ast.InlineFragmentNode, parent_type: Any
    ) -> None:
        target = parent_type
        if inline.type_condition is not None:
            type_name = inline.type_condition.name.value
            condition = self.schema.type_map.get(type_name)
            if condition is None:
                self._error(
                    f"Unknown type {type_name!r} in inline fragment.",
                    inline.type_condition,
                )
                return
            if not isinstance(condition, _COMPOSITE):
                self._error(
                    f"Inline fragment cannot condition on non-composite type "
                    f"{type_name!r}.",
                    inline.type_condition,
                )
                return
            if not self._types_overlap(parent_type, condition):
                self._error(
                    f"Fragment cannot be spread here as objects of type "
                    f"{_typename(condition)!r} can never be of type "
                    f"{_typename(parent_type)!r}.",
                    inline.type_condition,
                )
                return
            target = condition
        self._validate_selection_set(inline.selection_set, target)

    # -- possible types / overlap ---------------------------------------------

    def _possible_types(self, type_: Any) -> set[str]:
        if isinstance(type_, ObjectType):
            return {type_.name}
        if isinstance(type_, UnionType):
            return {member.name for member in type_.types}
        if isinstance(type_, InterfaceType):
            names = set()
            for candidate in self.schema.type_map.values():
                if isinstance(candidate, ObjectType) and any(
                    getattr(iface, "name", None) == type_.name
                    for iface in getattr(candidate, "interfaces", [])
                ):
                    names.add(candidate.name)
            return names
        return set()

    def _types_overlap(self, a: Any, b: Any) -> bool:
        if not isinstance(a, _COMPOSITE) or not isinstance(b, _COMPOSITE):
            return True  # cannot decide; don't produce a false positive
        return bool(self._possible_types(a) & self._possible_types(b))

    # -- overlapping fields can be merged -------------------------------------

    def _validate_field_merging(
        self, selection_set: ast.SelectionSetNode, parent_type: Any
    ) -> None:
        grouped = self._fields_by_response_key(selection_set, parent_type, set())
        for key, entries in grouped.items():
            first_node, _ = entries[0]
            for node, _ in entries[1:]:
                if node.name.value != first_node.name.value:
                    self._error(
                        f"Fields {key!r} conflict because {first_node.name.value!r} "
                        f"and {node.name.value!r} are different fields.",
                        node,
                    )
                    break
                if _arguments_map(first_node) != _arguments_map(node):
                    self._error(
                        f"Fields {key!r} conflict because they have differing "
                        f"arguments.",
                        node,
                    )
                    break
        # Recurse into the merged sub-selections for each response key.
        for entries in grouped.values():
            sub = [(n, pt) for (n, pt) in entries if n.selection_set is not None]
            if not sub:
                continue
            first_node, parent = sub[0]
            field_def = self._field_def(parent, first_node.name.value)
            if field_def is None:
                continue
            named = _named_type(field_def.type)
            if not isinstance(named, _COMPOSITE):
                continue
            combined = ast.SelectionSetNode(
                selections=[
                    selection
                    for node, _ in sub
                    for selection in node.selection_set.selections
                ]
            )
            self._validate_field_merging(combined, named)

    def _fields_by_response_key(
        self,
        selection_set: ast.SelectionSetNode,
        parent_type: Any,
        visited: set[str],
    ) -> dict[str, list[tuple[ast.FieldNode, Any]]]:
        grouped: dict[str, list[tuple[ast.FieldNode, Any]]] = {}
        for selection in selection_set.selections:
            if isinstance(selection, ast.FieldNode):
                key = (
                    selection.alias.value
                    if selection.alias
                    else selection.name.value
                )
                grouped.setdefault(key, []).append((selection, parent_type))
            elif isinstance(selection, ast.InlineFragmentNode):
                target = parent_type
                if selection.type_condition is not None:
                    target = self.schema.type_map.get(
                        selection.type_condition.name.value, parent_type
                    )
                self._merge_grouped(
                    grouped,
                    self._fields_by_response_key(
                        selection.selection_set, target, visited
                    ),
                )
            elif isinstance(selection, ast.FragmentSpreadNode):
                name = selection.name.value
                if name in self.fragments and name not in visited:
                    visited.add(name)
                    fragment = self.fragments[name]
                    target = self.schema.type_map.get(
                        fragment.type_condition.name.value, parent_type
                    )
                    self._merge_grouped(
                        grouped,
                        self._fields_by_response_key(
                            fragment.selection_set, target, visited
                        ),
                    )
        return grouped

    @staticmethod
    def _merge_grouped(into: dict, extra: dict) -> None:
        for key, entries in extra.items():
            into.setdefault(key, []).extend(entries)

    def _field_def(self, parent_type: Any, field_name: str) -> Any:
        if isinstance(parent_type, (ObjectType, InterfaceType)):
            return parent_type.fields.get(field_name)
        return None

    # -- variables ------------------------------------------------------------

    def _check_variables(self, operation: ast.OperationDefinitionNode) -> None:
        defined = {
            vd.variable.name.value for vd in operation.variable_definitions
        }
        for var_name, node in self._used_variables(operation.selection_set, set()):
            if var_name not in defined:
                self._error(f"Variable '${var_name}' is not defined.", node)

    def _used_variables(
        self, selection_set: ast.SelectionSetNode, seen_fragments: set[str]
    ) -> list[tuple[str, ast.Node]]:
        used: list[tuple[str, ast.Node]] = []
        for selection in selection_set.selections:
            for directive in getattr(selection, "directives", []):
                used.extend(self._variables_in_arguments(directive.arguments))
            if isinstance(selection, ast.FieldNode):
                used.extend(self._variables_in_arguments(selection.arguments))
                if selection.selection_set is not None:
                    used.extend(
                        self._used_variables(selection.selection_set, seen_fragments)
                    )
            elif isinstance(selection, ast.InlineFragmentNode):
                used.extend(
                    self._used_variables(selection.selection_set, seen_fragments)
                )
            elif isinstance(selection, ast.FragmentSpreadNode):
                frag_name = selection.name.value
                if frag_name in self.fragments and frag_name not in seen_fragments:
                    seen_fragments.add(frag_name)
                    used.extend(
                        self._used_variables(
                            self.fragments[frag_name].selection_set, seen_fragments
                        )
                    )
        return used

    def _variables_in_arguments(
        self, arguments: list[ast.ArgumentNode]
    ) -> list[tuple[str, ast.Node]]:
        used: list[tuple[str, ast.Node]] = []
        for argument in arguments:
            used.extend(self._variables_in_value(argument.value))
        return used

    def _variables_in_value(self, value: ast.ValueNode) -> list[tuple[str, ast.Node]]:
        if isinstance(value, ast.VariableNode):
            return [(value.name.value, value)]
        if isinstance(value, ast.ListValueNode):
            used: list[tuple[str, ast.Node]] = []
            for item in value.values:
                used.extend(self._variables_in_value(item))
            return used
        if isinstance(value, ast.ObjectValueNode):
            used = []
            for field in value.fields:
                used.extend(self._variables_in_value(field.value))
            return used
        return []


def _named_type(type_ref: Any) -> Any:
    while isinstance(type_ref, (NonNull, ListType)):
        type_ref = type_ref.of_type
    return type_ref


def _typename(type_: Any) -> str:
    return getattr(type_, "name", str(type_))


def _arguments_map(field: ast.FieldNode) -> dict[str, Any]:
    return {arg.name.value: _value_repr(arg.value) for arg in field.arguments}


def _value_repr(value: ast.ValueNode) -> Any:
    """A hashable, comparable representation of a literal value node."""
    if isinstance(value, ast.VariableNode):
        return ("var", value.name.value)
    if isinstance(value, ast.IntValueNode):
        return ("int", value.value)
    if isinstance(value, ast.FloatValueNode):
        return ("float", value.value)
    if isinstance(value, ast.StringValueNode):
        return ("str", value.value)
    if isinstance(value, ast.BooleanValueNode):
        return ("bool", value.value)
    if isinstance(value, ast.NullValueNode):
        return ("null",)
    if isinstance(value, ast.EnumValueNode):
        return ("enum", value.value)
    if isinstance(value, ast.ListValueNode):
        return ("list", tuple(_value_repr(item) for item in value.values))
    if isinstance(value, ast.ObjectValueNode):
        return (
            "object",
            tuple(
                sorted(
                    (field.name.value, _value_repr(field.value))
                    for field in value.fields
                )
            ),
        )
    return ("unknown",)


__all__ = ["validate"]
