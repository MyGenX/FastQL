"""Internal registry for decorator-produced metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastql.types import Field, NamedType, ObjectType


@dataclass
class OperationDefinition:
    """A root operation field registered by an operation decorator."""

    operation: str
    name: str
    field: Field
    resolver: Any


@dataclass
class DecoratorRegistry:
    """Collects decorated types and root operation fields."""

    types_by_python: dict[Any, NamedType] = field(default_factory=dict)
    types_by_name: dict[str, NamedType] = field(default_factory=dict)
    operations: dict[str, dict[str, OperationDefinition]] = field(
        default_factory=lambda: {"query": {}, "mutation": {}, "subscription": {}}
    )
    root_types_by_python: dict[Any, ObjectType] = field(default_factory=dict)
    root_classes: dict[str, list[type]] = field(
        default_factory=lambda: {"query": [], "mutation": [], "subscription": []}
    )

    def register_type(self, python_obj: Any, type_: NamedType) -> NamedType:
        self.types_by_python[python_obj] = type_
        self.types_by_name[type_.name] = type_
        setattr(python_obj, "__fastql_type__", type_)
        return type_

    def register_operation(
        self, operation: str, name: str, field: Field, resolver: Any
    ) -> OperationDefinition:
        existing = self.operations[operation].get(name)
        if existing is not None and existing.resolver is not resolver:
            raise ValueError(
                f"Duplicate {operation} field {name!r}: already registered by another "
                "operation. Rename one of them with Field(name=...)."
            )
        definition = OperationDefinition(operation, name, field, resolver)
        self.operations[operation][name] = definition
        try:
            setattr(resolver, "__fastql_operation__", definition)
        except (AttributeError, TypeError):
            pass  # bound methods don't accept attributes; the registry entry suffices
        return definition

    def register_root(self, operation: str, python_obj: type, type_: ObjectType) -> None:
        self.root_types_by_python[python_obj] = type_
        if python_obj not in self.root_classes[operation]:
            self.root_classes[operation].append(python_obj)
        setattr(python_obj, "__fastql_type__", type_)
        setattr(python_obj, "__fastql_root__", operation)

    def clear(self) -> None:
        self.types_by_python.clear()
        self.types_by_name.clear()
        self.operations = {"query": {}, "mutation": {}, "subscription": {}}
        self.root_types_by_python.clear()
        self.root_classes = {"query": [], "mutation": [], "subscription": []}


default_registry = DecoratorRegistry()


__all__ = ["DecoratorRegistry", "OperationDefinition", "default_registry"]
