"""Optional Pydantic integration.

Install ``mygenx-fastql[pydantic]``. Derive a FastQL output type or input type
from a Pydantic (v2) model, mapping the model's fields, optionality, and defaults
to GraphQL fields/arguments. When a Pydantic model backs an input type, the
coerced GraphQL input is constructed *through* the model, so its validators run
and validation failures surface as GraphQL errors.

The core package never imports this module; ``import fastql`` works without
Pydantic installed.
"""

from __future__ import annotations

from typing import Any, TypeVar

from fastql.decorators.annotations import resolve_type_hint
from fastql.decorators.registry import default_registry
from fastql.types import (
    Field as IRField,
    InputField,
    InputObjectType,
    ObjectType,
)

_T = TypeVar("_T", bound=type)


def _require_pydantic() -> Any:
    try:
        import pydantic
    except ImportError as error:  # pragma: no cover - exercised via import guard
        raise ImportError(
            "The Pydantic integration requires 'mygenx-fastql[pydantic]'."
        ) from error
    return pydantic


def _model_fields(model: type) -> dict[str, Any]:
    fields = getattr(model, "model_fields", None)
    if not isinstance(fields, dict):
        raise TypeError(f"{model.__name__!r} is not a Pydantic v2 BaseModel.")
    return fields


def pydantic_type(
    model: _T | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> _T:
    """Register a Pydantic model as a FastQL **output** type and return it.

    Usable as ``pydantic_type(Model)`` or as a decorator ``@pydantic_type``.
    """

    def register(target: type) -> type:
        _require_pydantic()
        gql_name = name or target.__name__
        fields: dict[str, IRField] = {}
        for field_name, info in _model_fields(target).items():
            fields[field_name] = IRField(
                resolve_type_hint(info.annotation, module=target.__module__),
                description=info.description,
                python_name=field_name,
            )
        type_ = ObjectType(
            gql_name,
            fields=fields,
            description=description or target.__doc__,
        )
        default_registry.register_type(target, type_)
        return target

    return register(model) if model is not None else register  # type: ignore[return-value]


def pydantic_input(
    model: _T | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> _T:
    """Register a Pydantic model as a FastQL **input** type and return it.

    The GraphQL input object carries each model field's optionality and defaults.
    At execution the coerced values are passed to the model constructor, so
    Pydantic validation runs and failures surface as GraphQL errors.

    Usable as ``pydantic_input(Model)`` or as a decorator ``@pydantic_input``.
    """

    def register(target: type) -> type:
        _require_pydantic()
        gql_name = name or target.__name__
        fields: dict[str, InputField] = {}
        for field_name, info in _model_fields(target).items():
            default_factory = getattr(info, "default_factory", None)
            if default_factory is not None:
                default_value = None
            elif info.is_required():
                default_value = None
            else:
                default_value = info.default
            fields[field_name] = InputField(
                resolve_type_hint(info.annotation, module=target.__module__),
                default_value=default_value,
                description=info.description,
                python_name=field_name,
                default_factory=default_factory,
            )
        type_ = InputObjectType(
            gql_name,
            fields=fields,
            description=description or target.__doc__,
            python_type=target,
        )
        default_registry.register_type(target, type_)
        return target

    return register(model) if model is not None else register  # type: ignore[return-value]


__all__ = ["pydantic_input", "pydantic_type"]
