"""Decorator authoring surface: ``@Type``, ``@Query``, ``@Field``, and friends."""
"""Decorator authoring surface for code-first schemas."""

from fastql.decorators.annotations import TypeReference, resolve_type_hint
from fastql.decorators.enum import Enum
from fastql.decorators.field import (
    Arg,
    Argument,
    BasePermission,
    Field,
    FieldExtension,
    FieldSpec,
)
from fastql.decorators.object import Input, Interface, Type
from fastql.decorators.operations import Mutation, Query, Subscription
from fastql.decorators.registry import DecoratorRegistry, OperationDefinition, default_registry
from fastql.decorators.scalar import Scalar
from fastql.decorators.union import Union

__all__ = [
    "DecoratorRegistry",
    "Arg",
    "Argument",
    "BasePermission",
    "Enum",
    "Field",
    "FieldSpec",
    "FieldExtension",
    "Input",
    "Interface",
    "Mutation",
    "OperationDefinition",
    "Query",
    "Scalar",
    "Subscription",
    "Type",
    "TypeReference",
    "Union",
    "default_registry",
    "resolve_type_hint",
]
