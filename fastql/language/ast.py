"""AST node definitions for parsed GraphQL documents.

Every node carries a :class:`Location` so downstream layers (validation,
execution, error reporting) can point back at the originating source span.
The node set covers executable documents: operations, fragments, selections,
arguments, directives, values, and type references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from fastql.language.source import Source


@dataclass(frozen=True)
class Location:
    """A span ``[start, end)`` of character offsets within a :class:`Source`."""

    start: int
    end: int
    source: "Source"


class Node:
    """Base class for all AST nodes."""

    __slots__ = ()
    loc: Optional[Location]


# --- Name ---------------------------------------------------------------------


@dataclass
class NameNode(Node):
    value: str
    loc: Optional[Location] = None


# --- Document & definitions ---------------------------------------------------


@dataclass
class DocumentNode(Node):
    definitions: list["DefinitionNode"]
    loc: Optional[Location] = None


@dataclass
class OperationDefinitionNode(Node):
    operation: str  # "query" | "mutation" | "subscription"
    selection_set: "SelectionSetNode"
    name: Optional[NameNode] = None
    variable_definitions: list["VariableDefinitionNode"] = field(default_factory=list)
    directives: list["DirectiveNode"] = field(default_factory=list)
    loc: Optional[Location] = None


@dataclass
class VariableDefinitionNode(Node):
    variable: "VariableNode"
    type: "TypeNode"
    default_value: Optional["ValueNode"] = None
    directives: list["DirectiveNode"] = field(default_factory=list)
    loc: Optional[Location] = None


@dataclass
class FragmentDefinitionNode(Node):
    name: NameNode
    type_condition: "NamedTypeNode"
    selection_set: "SelectionSetNode"
    directives: list["DirectiveNode"] = field(default_factory=list)
    loc: Optional[Location] = None


DefinitionNode = Union[OperationDefinitionNode, FragmentDefinitionNode]


# --- Selections ---------------------------------------------------------------


@dataclass
class SelectionSetNode(Node):
    selections: list["SelectionNode"]
    loc: Optional[Location] = None


@dataclass
class FieldNode(Node):
    name: NameNode
    alias: Optional[NameNode] = None
    arguments: list["ArgumentNode"] = field(default_factory=list)
    directives: list["DirectiveNode"] = field(default_factory=list)
    selection_set: Optional[SelectionSetNode] = None
    loc: Optional[Location] = None


@dataclass
class FragmentSpreadNode(Node):
    name: NameNode
    directives: list["DirectiveNode"] = field(default_factory=list)
    loc: Optional[Location] = None


@dataclass
class InlineFragmentNode(Node):
    selection_set: SelectionSetNode
    type_condition: Optional["NamedTypeNode"] = None
    directives: list["DirectiveNode"] = field(default_factory=list)
    loc: Optional[Location] = None


SelectionNode = Union[FieldNode, FragmentSpreadNode, InlineFragmentNode]


# --- Arguments & directives ---------------------------------------------------


@dataclass
class ArgumentNode(Node):
    name: NameNode
    value: "ValueNode"
    loc: Optional[Location] = None


@dataclass
class DirectiveNode(Node):
    name: NameNode
    arguments: list[ArgumentNode] = field(default_factory=list)
    loc: Optional[Location] = None


# --- Values -------------------------------------------------------------------


@dataclass
class VariableNode(Node):
    name: NameNode
    loc: Optional[Location] = None


@dataclass
class IntValueNode(Node):
    value: str
    loc: Optional[Location] = None


@dataclass
class FloatValueNode(Node):
    value: str
    loc: Optional[Location] = None


@dataclass
class StringValueNode(Node):
    value: str
    block: bool = False
    loc: Optional[Location] = None


@dataclass
class BooleanValueNode(Node):
    value: bool
    loc: Optional[Location] = None


@dataclass
class NullValueNode(Node):
    loc: Optional[Location] = None


@dataclass
class EnumValueNode(Node):
    value: str
    loc: Optional[Location] = None


@dataclass
class ListValueNode(Node):
    values: list["ValueNode"]
    loc: Optional[Location] = None


@dataclass
class ObjectFieldNode(Node):
    name: NameNode
    value: "ValueNode"
    loc: Optional[Location] = None


@dataclass
class ObjectValueNode(Node):
    fields: list[ObjectFieldNode]
    loc: Optional[Location] = None


ValueNode = Union[
    VariableNode,
    IntValueNode,
    FloatValueNode,
    StringValueNode,
    BooleanValueNode,
    NullValueNode,
    EnumValueNode,
    ListValueNode,
    ObjectValueNode,
]


# --- Type references ----------------------------------------------------------


@dataclass
class NamedTypeNode(Node):
    name: NameNode
    loc: Optional[Location] = None


@dataclass
class ListTypeNode(Node):
    type: "TypeNode"
    loc: Optional[Location] = None


@dataclass
class NonNullTypeNode(Node):
    type: Union[NamedTypeNode, ListTypeNode]
    loc: Optional[Location] = None


TypeNode = Union[NamedTypeNode, ListTypeNode, NonNullTypeNode]
