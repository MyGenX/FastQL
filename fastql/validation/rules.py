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
        for definition in self.document.definitions:
            if isinstance(definition, ast.OperationDefinitionNode):
                self._validate_operation(definition)
            elif isinstance(definition, ast.FragmentDefinitionNode):
                self._validate_fragment_definition(definition)
        return self.errors

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
        self._validate_selection_set(operation.selection_set, root)
        self._check_variables(operation)

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
                self._validate_fragment_spread(selection)
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

    def _check_argument_value(self, argument: ast.ArgumentNode, arg_def: Any) -> None:
        value = argument.value
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

    # -- fragments ------------------------------------------------------------

    def _validate_fragment_spread(self, spread: ast.FragmentSpreadNode) -> None:
        if spread.name.value not in self.fragments:
            self._error(f"Unknown fragment {spread.name.value!r}.", spread)

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
            target = condition
        self._validate_selection_set(inline.selection_set, target)

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


__all__ = ["validate"]
