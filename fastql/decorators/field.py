"""Field descriptor and method decorator."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable

from fastql.types import AppliedDirective

_UNSET = object()


@dataclass(frozen=True)
class Argument:
    """GraphQL argument metadata for ``Annotated`` or :func:`Arg`."""

    name: str | None = None
    description: str | None = None
    deprecation_reason: str | None = None
    default: Any = _UNSET
    directives: tuple[AppliedDirective, ...] = ()


def Arg(
    *,
    name: str | None = None,
    description: str | None = None,
    deprecated: str | None = None,
    deprecation_reason: str | None = None,
    default: Any = _UNSET,
    directives: list[AppliedDirective] | tuple[AppliedDirective, ...] | None = None,
) -> Argument:
    """Parameter-default form of :class:`Argument` metadata."""

    return Argument(
        name=name,
        description=description,
        deprecation_reason=(
            deprecation_reason if deprecation_reason is not None else deprecated
        ),
        default=default,
        directives=tuple(directives or ()),
    )


class FieldExtension:
    """Base class for ordered field resolver extensions."""

    def resolve(self, next_, source, info, **kwargs):
        return next_(source, info, **kwargs)


class BasePermission:
    """Base class for declarative field permissions."""

    message = "Permission denied"

    def has_permission(self, source, info, **kwargs) -> bool:
        return False


@dataclass
class FieldSpec:
    """Metadata captured by ``Field(...)`` before schema building."""

    graphql_name: str | None = None
    description: str | None = None
    deprecation_reason: str | None = None
    type: Any = None
    default_value: Any = _UNSET
    default_factory: Callable[[], Any] | None = None
    resolver: Callable[..., Any] | None = None
    python_name: str | None = None
    arguments: dict[str, Argument] = field(default_factory=dict)
    directives: list[AppliedDirective] = field(default_factory=list)
    extensions: list[Any] = field(default_factory=list)
    permission_classes: list[Any] = field(default_factory=list)
    private: bool = False
    external: bool = False

    def __set_name__(self, owner: type, name: str) -> None:
        self.python_name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None or self.resolver is not None:
            return self
        if self.python_name is None:
            return self.default_value if self.default_value is not _UNSET else None
        return instance.__dict__.get(
            self.python_name,
            self.default_value if self.default_value is not _UNSET else None,
        )

    def __set__(self, instance: Any, value: Any) -> None:
        if self.python_name is None:
            raise AttributeError("Cannot assign to unnamed Field descriptor")
        instance.__dict__[self.python_name] = value

    def __call__(self, resolver: Callable[..., Any]) -> "FieldSpec":
        field = replace(self, resolver=resolver, python_name=getattr(resolver, "__name__", None))
        setattr(resolver, "__fastql_field__", field)
        return field

    @property
    def name(self) -> str | None:
        return self.graphql_name

    @property
    def deprecated(self) -> str | None:
        return self.deprecation_reason

    @property
    def is_computed(self) -> bool:
        """True for resolver-backed fields (``@Field`` methods or ``Field(resolver=...)``)."""
        return self.resolver is not None

    @property
    def has_default(self) -> bool:
        return self.default_value is not _UNSET


def Field(
    resolver: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    deprecated: str | None = None,
    deprecation_reason: str | None = None,
    type: Any = None,
    type_: Any = None,
    default: Any = _UNSET,
    default_factory: Callable[[], Any] | None = None,
    arguments: dict[str, Argument] | None = None,
    directives: list[AppliedDirective] | None = None,
    extensions: list[Any] | None = None,
    permission_classes: list[Any] | None = None,
    private: bool = False,
    external: bool = False,
) -> FieldSpec:
    """Capture GraphQL field metadata as a descriptor or method decorator."""

    if default is not _UNSET and default_factory is not None:
        raise TypeError("Field cannot define both default and default_factory")
    spec = FieldSpec(
        graphql_name=name,
        description=description,
        deprecation_reason=deprecation_reason if deprecation_reason is not None else deprecated,
        type=type if type is not None else type_,
        default_value=default,
        default_factory=default_factory,
        arguments=dict(arguments or {}),
        directives=list(directives or []),
        extensions=list(extensions or []),
        permission_classes=list(permission_classes or []),
        private=private,
        external=external,
    )
    if resolver is not None:
        return spec(resolver)
    return spec


__all__ = [
    "Arg",
    "Argument",
    "BasePermission",
    "Field",
    "FieldExtension",
    "FieldSpec",
]
