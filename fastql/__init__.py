"""FastQL — a code-first, decorator-driven GraphQL framework for Python.

Define types and operations with decorators, build a schema, and execute
operations — all without any web framework. The core turns Python values into a
:class:`~fastql.types.schema.Schema` and runs operations through a hand-built,
async-first engine.

    from fastql import Type, Query, Schema, Context, execute

    @Type
    class User:
        id: int
        name: str

    @Query
    class QueryRoot:
        @Field
        async def user(self, id: int, ctx: Context) -> "User":
            return ctx.users[id]

    schema = Schema(query=QueryRoot)
    result = await execute(schema, "{ user(id: 1) { id name } }", context=ctx)
"""

from fastql.context import (
    Context,
    Info,
    ResolveInfo,
    provides,
    register_dependency,
)
from fastql.dataloader import DataLoader, DataLoaderError, get_loader
from fastql.decorators import (
    Arg,
    Argument,
    BasePermission,
    Enum,
    Field,
    FieldExtension,
    Input,
    Interface,
    Mutation,
    Query,
    Scalar,
    Subscription,
    Type,
    Union,
)
from fastql.errors import GraphQLError, GraphQLSyntaxError, ValidationError
from fastql.execution import ExecutionResult, execute
from fastql.extensions import SchemaExtension
from fastql.language import parse
from fastql.registry import TypeRegistry, default_registry
from fastql.schema_builder import SchemaBuildError, build_schema
from fastql.sdl import print_schema
from fastql.types import (
    AppliedDirective,
    Boolean,
    Float,
    ID,
    Int,
    ListType,
    NonNull,
    Schema,
    SchemaConfig,
    String,
)
from fastql.validation import validate

__version__ = "0.0.1"

__all__ = [
    "__version__",
    # Decorators
    "Type",
    "Input",
    "Interface",
    "Enum",
    "Union",
    "Scalar",
    "Query",
    "Mutation",
    "Subscription",
    "Field",
    "Arg",
    "Argument",
    "AppliedDirective",
    "BasePermission",
    "FieldExtension",
    "SchemaExtension",
    # Context / DI
    "Context",
    "Info",
    "ResolveInfo",
    "register_dependency",
    "provides",
    # DataLoader (request-scoped batch loading)
    "DataLoader",
    "DataLoaderError",
    "get_loader",
    # Built-in scalars and wrappers
    "Int",
    "Float",
    "String",
    "Boolean",
    "ID",
    "NonNull",
    "ListType",
    # Schema building and execution
    "Schema",
    "SchemaConfig",
    "build_schema",
    "SchemaBuildError",
    "execute",
    "ExecutionResult",
    "validate",
    "parse",
    "print_schema",
    # Dev server (lazy — keeps the agnostic core free of the HTTP layer)
    "serve",
    "start_server",
    # Registry
    "TypeRegistry",
    "default_registry",
    # Errors
    "GraphQLError",
    "GraphQLSyntaxError",
    "ValidationError",
]


def __getattr__(name: str):
    # `serve` / `start_server` live in fastql.server, which imports asyncio HTTP
    # machinery. Import them lazily so the agnostic core never pulls in the
    # transport layer just by `import fastql`.
    if name in ("serve", "start_server"):
        from fastql import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
