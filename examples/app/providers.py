"""Dependency injection via ``register_dependency``.

A resolver can declare a parameter typed as a registered service (here ``Clock``) and
the executor will build and inject it — once per operation — without it being a GraphQL
argument. This keeps cross-cutting collaborators (clocks, db sessions, clients) out of
the schema while still being testable.

:func:`register_dependencies` is idempotent and is called on import; tests that clear
the global dependency registry can call it again to re-register.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastql import register_dependency


class Clock:
    """A trivial injectable service."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def provide_clock(context) -> Clock:
    return Clock()


def register_dependencies() -> None:
    register_dependency(Clock, provide_clock)


register_dependencies()

__all__ = ["Clock", "provide_clock", "register_dependencies"]
