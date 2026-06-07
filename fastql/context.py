"""Context object and resolver dependency injection.

Resolvers stay plain functions. The executor inspects each resolver's signature
and binds parameters by role:

* a parameter whose name matches a GraphQL field argument receives that argument;
* a parameter named ``self``/``parent``/``root``/``source`` receives the parent value;
* a parameter typed :class:`Context` (or named ``context``/``ctx``) receives the
  execution context passed to ``execute``;
* a parameter typed :class:`ResolveInfo` (or named ``info``) receives resolve info;
* a parameter typed as a registered dependency receives the value its provider
  produces from the active context.

Type-based detection is primary (a ``Context``-typed parameter of *any* name is
injected); the conventional names are honored as a convenience.
"""

from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar, get_origin

_PARENT_NAMES = {"self", "parent", "root", "source"}
_CONTEXT_NAMES = {"context", "ctx"}
_INFO_NAMES = {"info"}


class Context:
    """Marker base class for the per-request execution context.

    A resolver parameter annotated with ``Context`` (or a subclass) receives the
    value passed to ``execute(context=...)``. Subclass it to add typed fields, or
    pass any object and annotate the parameter with ``Context``.
    """


ContextType = TypeVar("ContextType")
RootType = TypeVar("RootType")


@dataclass
class Info(Generic[ContextType, RootType]):
    """Metadata passed to resolvers that request an ``info`` parameter."""

    field_name: str
    python_name: str
    path: list[Any]
    parent_type: Any
    schema: Any
    context: ContextType
    root_value: RootType | None
    variable_values: dict[str, Any]
    operation: Any = None
    selected_fields: list[Any] = field(default_factory=list)


ResolveInfo = Info


# --- dependency providers ----------------------------------------------------


@dataclass
class DependencyRegistry:
    """Maps a Python type to a provider that derives it from the context."""

    providers: dict[type, Callable[[Any], Any]] = field(default_factory=dict)

    def register(self, type_: type, provider: Callable[[Any], Any]) -> None:
        self.providers[type_] = provider

    def get(self, type_: Any) -> Callable[[Any], Any] | None:
        if isinstance(type_, type):
            return self.providers.get(type_)
        return None

    def clear(self) -> None:
        self.providers.clear()


default_dependencies = DependencyRegistry()


def register_dependency(type_: type, provider: Callable[[Any], Any]) -> None:
    """Register ``provider`` to produce ``type_`` from the active context."""
    default_dependencies.register(type_, provider)


def provides(type_: type) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
    """Decorator form of :func:`register_dependency`."""

    def decorate(provider: Callable[[Any], Any]) -> Callable[[Any], Any]:
        default_dependencies.register(type_, provider)
        return provider

    return decorate


# --- injection plan ----------------------------------------------------------


@dataclass(frozen=True)
class Binding:
    """How a single resolver parameter should be supplied at call time."""

    name: str
    role: str  # "arg" | "parent" | "context" | "info" | "dependency"
    provider: Callable[[Any], Any] | None = None
    dependency_type: type | None = None


def build_injection_plan(
    resolver: Callable[..., Any],
    dependencies: DependencyRegistry | None = None,
) -> list[Binding]:
    """Classify each resolver parameter into an injection :class:`Binding`."""
    deps = dependencies or default_dependencies
    hints = _resolve_hints(resolver)
    plan: list[Binding] = []
    try:
        signature = inspect.signature(resolver)
    except (TypeError, ValueError):
        return plan
    for parameter in signature.parameters.values():
        if parameter.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            continue
        annotation = hints.get(parameter.name, parameter.annotation)
        role, provider = _classify(parameter.name, annotation, deps)
        dependency_type = annotation if role == "dependency" else None
        plan.append(Binding(parameter.name, role, provider, dependency_type))
    return plan


def injected_parameter_names(
    resolver: Callable[..., Any],
    dependencies: DependencyRegistry | None = None,
) -> set[str]:
    """Return parameter names that are injected (i.e. not GraphQL arguments)."""
    return {
        binding.name
        for binding in build_injection_plan(resolver, dependencies)
        if binding.role != "arg"
    }


def _classify(name, annotation, deps) -> tuple[str, Callable[[Any], Any] | None]:
    origin = get_origin(annotation)
    if origin is Info:
        return "info", None
    if name in _PARENT_NAMES:
        return "parent", None
    if isinstance(annotation, type):
        provider = deps.get(annotation)
        if provider is not None:
            return "dependency", provider
        if issubclass(annotation, Context):
            return "context", None
        if annotation is Info or annotation is ResolveInfo:
            return "info", None
    if name in _CONTEXT_NAMES:
        return "context", None
    if name in _INFO_NAMES:
        return "info", None
    return "arg", None


def _resolve_hints(resolver: Callable[..., Any]) -> dict[str, Any]:
    """Best-effort resolution of parameter annotations to runtime objects.

    Falls back to per-parameter evaluation so that one unresolvable annotation
    (e.g. a forward-referenced return type) does not hide the others.
    """
    try:
        return typing.get_type_hints(resolver)
    except Exception:
        pass
    hints: dict[str, Any] = {}
    globalns = getattr(resolver, "__globals__", {})
    try:
        signature = inspect.signature(resolver)
    except (TypeError, ValueError):
        return hints
    for name, parameter in signature.parameters.items():
        annotation = parameter.annotation
        if isinstance(annotation, str):
            try:
                hints[name] = eval(annotation, globalns)  # noqa: S307 - trusted code
            except Exception:
                continue
        elif annotation is not inspect.Parameter.empty:
            hints[name] = annotation
    return hints


__all__ = [
    "Context",
    "Info",
    "ResolveInfo",
    "Binding",
    "DependencyRegistry",
    "default_dependencies",
    "register_dependency",
    "provides",
    "build_injection_plan",
    "injected_parameter_names",
]
