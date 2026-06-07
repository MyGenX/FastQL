"""Root operation class decorators."""

from __future__ import annotations

from fastql.decorators.definition import decorate_definition


def _operation(kind, target=None, *, name=None, description=None):
    def decorate(obj):
        if not isinstance(obj, type):
            raise TypeError(
                f"@{kind.title()} can only decorate a class; move {obj.__name__!r} "
                "to an @Field method on a root class"
            )
        return decorate_definition(
            kind, obj, name=name, description=description
        )

    return decorate(target) if target is not None else decorate


def Query(resolver=None, *, name=None, description=None):
    return _operation("query", resolver, name=name, description=description)


def Mutation(resolver=None, *, name=None, description=None):
    return _operation("mutation", resolver, name=name, description=description)


def Subscription(resolver=None, *, name=None, description=None):
    return _operation(
        "subscription",
        resolver,
        name=name,
        description=description,
    )


__all__ = ["Mutation", "Query", "Subscription"]
