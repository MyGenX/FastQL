"""Author-defined GraphQL directives.

``@Directive`` turns a class into a :class:`~fastql.types.DirectiveDefinition`: the
class name is the directive name, annotated attributes become arguments (types from
hints, defaults from class attributes), and ``locations``/``repeatable``/``description``
come from the decorator. Applied directives are attached to definitions via
:class:`~fastql.types.AppliedDirective` and validated/coerced at build time.

    @Directive(locations=["FIELD_DEFINITION", "OBJECT"], repeatable=True)
    class tag:
        name: str
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from fastql.decorators.annotations import resolve_type_hint
from fastql.decorators.field import _UNSET
from fastql.decorators.registry import default_registry
from fastql.types import Argument as IRArgument
from fastql.types import DirectiveDefinition


def Directive(
    cls: type | None = None,
    *,
    locations: Sequence[str],
    name: str | None = None,
    description: str | None = None,
    repeatable: bool = False,
) -> Any:
    """Register ``cls`` as a custom schema directive definition."""

    def decorate(target: type) -> type:
        gql_name = name or target.__name__
        definition = DirectiveDefinition(
            name=gql_name,
            locations=list(locations),
            args=_directive_arguments(target),
            description=description if description is not None else (target.__doc__ or None),
            is_repeatable=repeatable,
        )
        default_registry.register_directive(target, definition)
        return target

    return decorate(cls) if cls is not None else decorate


def _directive_arguments(target: type) -> dict[str, IRArgument]:
    annotations: dict[str, Any] = getattr(target, "__annotations__", {})
    args: dict[str, IRArgument] = {}
    for python_name, hint in annotations.items():
        default = getattr(target, python_name, _UNSET)
        args[python_name] = IRArgument(
            resolve_type_hint(hint, module=getattr(target, "__module__", None)),
            default_value=None if default is _UNSET else default,
            python_name=python_name,
        )
    return args


__all__ = ["Directive"]
