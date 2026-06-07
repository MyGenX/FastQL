"""The async-first GraphQL executor.

``execute`` parses (when given a string), validates, selects the operation,
coerces variables, and resolves fields. Sibling fields resolve concurrently via
``asyncio.gather``; both ``async def`` and plain ``def`` resolvers are supported.
Field errors are captured as :class:`GraphQLError` with a path, the field is set
to null, and null propagates to the nearest nullable parent per the GraphQL spec
while unaffected fields keep resolving.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any

from fastql.context import Info, ResolveInfo, build_injection_plan
from fastql.errors import GraphQLError, GraphQLSyntaxError
from fastql.execution.collect_fields import collect_fields
from fastql.extensions import (
    collect_results,
    has_resolve_override,
    instantiate_extensions,
    phase,
)
from fastql.execution.values import (
    coerce_argument_values,
    coerce_variable_values,
    complete_leaf_value,
)
from fastql.language import ast
from fastql.language.parser import parse
from fastql.language.source import Source
from fastql.types import EnumType, InterfaceType, ObjectType, ScalarType, UnionType
from fastql.types.wrappers import ListType, NonNull
from fastql.validation import validate


@dataclass
class ExecutionResult:
    """The result of executing an operation: ``data``, ``errors``, ``extensions``."""

    data: Any = None
    errors: list[GraphQLError] = field(default_factory=list)
    extensions: dict[str, Any] | None = None
    executed: bool = True

    def formatted(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.executed:
            out["data"] = self.data
        if self.errors:
            out["errors"] = [e.formatted() for e in self.errors]
        if self.extensions:
            out["extensions"] = self.extensions
        return out


class _NullBubble(Exception):
    """Internal signal that a non-null position produced null and must propagate."""


_BUBBLE = object()


async def execute(
    schema: Any,
    query: str | Source | ast.DocumentNode,
    variable_values: dict[str, Any] | None = None,
    context: Any = None,
    operation_name: str | None = None,
    root_value: Any = None,
) -> ExecutionResult:
    extensions = instantiate_extensions(getattr(schema, "extensions", None))
    async with phase(extensions, "on_operation"):
        result = await _run_pipeline(
            schema, query, variable_values, context,
            operation_name, root_value, extensions,
        )
    if extensions:
        extra = await collect_results(extensions)
        if extra:
            result.extensions = {**(result.extensions or {}), **extra}
    return result


async def _run_pipeline(
    schema, query, variable_values, context, operation_name, root_value, extensions
) -> ExecutionResult:
    async with phase(extensions, "on_parse"):
        if isinstance(query, (str, Source)):
            try:
                document = parse(query)
            except GraphQLSyntaxError as error:
                return ExecutionResult(errors=[error], executed=False)
        else:
            document = query

    operation, op_error = _get_operation(document, operation_name)
    if op_error is not None:
        return ExecutionResult(errors=[op_error], executed=False)

    async with phase(extensions, "on_validate"):
        validation_errors = validate(schema, document)
    if validation_errors:
        return ExecutionResult(errors=list(validation_errors), executed=False)

    try:
        coerced_variables = coerce_variable_values(
            schema, operation, variable_values or {}
        )
    except GraphQLError as error:
        return ExecutionResult(errors=[error], executed=False)

    async with phase(extensions, "on_execute"):
        executor = _Executor(
            schema, document, coerced_variables, context, operation,
            root_value, extensions,
        )
        data = await executor.execute_operation(operation)
        result = ExecutionResult(data=data, errors=executor.errors)
    return result


def _get_operation(
    document: ast.DocumentNode, operation_name: str | None
) -> tuple[ast.OperationDefinitionNode | None, GraphQLError | None]:
    operations = [
        d for d in document.definitions if isinstance(d, ast.OperationDefinitionNode)
    ]
    if not operations:
        return None, GraphQLError("Document does not contain an operation to execute.")
    if operation_name is None:
        if len(operations) > 1:
            return None, GraphQLError(
                "Must provide operation name when multiple operations are present."
            )
        return operations[0], None
    for operation in operations:
        if operation.name is not None and operation.name.value == operation_name:
            return operation, None
    return None, GraphQLError(f"Unknown operation named {operation_name!r}.")


class _Executor:
    def __init__(
        self, schema, document, variable_values, context, operation, root_value,
        extensions=(),
    ) -> None:
        self.schema = schema
        self.variable_values = variable_values
        self.context = context
        self.errors: list[GraphQLError] = []
        self.operation = operation
        self.root_value = root_value
        self.resolve_extensions = [
            ext for ext in extensions if has_resolve_override(ext)
        ]
        self.root_instances: dict[type, Any] = {}
        self.dependency_values: dict[type, Any] = {}
        self.fragments = {
            d.name.value: d
            for d in document.definitions
            if isinstance(d, ast.FragmentDefinitionNode)
        }

    async def execute_operation(self, operation: ast.OperationDefinitionNode) -> Any:
        root_type = self._root_type(operation.operation)
        if root_type is None:
            self.errors.append(
                GraphQLError(
                    f"Schema is not configured to execute {operation.operation} operations."
                )
            )
            return None
        grouped = collect_fields(
            self.schema, root_type, operation.selection_set,
            self.variable_values, self.fragments,
        )
        serial = operation.operation == "mutation"
        try:
            return await self._execute_fields(
                root_type, self.root_value, grouped, [], serial
            )
        except _NullBubble:
            return None

    def _root_type(self, operation: str):
        return {
            "query": self.schema.query,
            "mutation": self.schema.mutation,
            "subscription": self.schema.subscription,
        }.get(operation)

    # -- field execution ------------------------------------------------------

    async def _execute_fields(self, parent_type, source, grouped, path, serial):
        keys = list(grouped)
        results: dict[str, Any] = {}
        if serial:
            for key in keys:
                results[key] = await self._execute_field(
                    parent_type, source, grouped[key], path + [key]
                )
            return results

        gathered = await asyncio.gather(
            *(
                self._execute_field(parent_type, source, grouped[key], path + [key])
                for key in keys
            ),
            return_exceptions=True,
        )
        bubble = False
        for key, outcome in zip(keys, gathered):
            if isinstance(outcome, _NullBubble):
                bubble = True
                results[key] = None
            elif isinstance(outcome, BaseException):
                raise outcome
            else:
                results[key] = outcome
        if bubble:
            raise _NullBubble()
        return results

    async def _execute_field(self, parent_type, source, field_nodes, path):
        node = field_nodes[0]
        field_name = node.name.value

        if field_name == "__typename":
            return parent_type.name

        field_def = getattr(parent_type, "fields", {}).get(field_name)
        if field_def is None:
            return None  # unreachable after validation

        info = Info(
            field_name=field_name,
            python_name=getattr(field_def, "python_name", None) or field_name,
            path=list(path),
            parent_type=parent_type,
            schema=self.schema,
            context=self.context,
            root_value=self.root_value,
            variable_values=self.variable_values,
            operation=self.operation,
            selected_fields=list(field_nodes),
        )

        try:
            args = coerce_argument_values(field_def, node, self.variable_values)
        except GraphQLError as error:
            self._record(error, path, node)
            return self._null_or_bubble(field_def.type)

        try:
            result = await self._resolve_field(field_def, source, args, info)
            return await self._complete_value(field_def.type, field_nodes, path, result, info)
        except _NullBubble:
            raise
        except GraphQLError as error:
            self._record(error, path, node)
            return self._null_or_bubble(field_def.type)
        except Exception as error:  # resolver raised
            self._record(GraphQLError(str(error), original_error=error), path, node)
            return self._null_or_bubble(field_def.type)

    def _null_or_bubble(self, type_ref):
        if isinstance(type_ref, NonNull):
            raise _NullBubble()
        return None

    # -- value completion -----------------------------------------------------

    async def _complete_value(self, type_ref, field_nodes, path, result, info):
        if isinstance(type_ref, NonNull):
            completed = await self._complete_value(
                type_ref.of_type, field_nodes, path, result, info
            )
            if completed is None:
                if result is None:
                    self._record(
                        GraphQLError(
                            f"Cannot return null for non-nullable field "
                            f"{field_nodes[0].name.value!r}."
                        ),
                        path,
                        field_nodes[0],
                    )
                raise _NullBubble()
            return completed

        if result is None:
            return None

        if isinstance(type_ref, ListType):
            return await self._complete_list(type_ref, field_nodes, path, result, info)

        if isinstance(type_ref, (ScalarType, EnumType)):
            try:
                return complete_leaf_value(type_ref, result)
            except GraphQLError as error:
                self._record(error, path, field_nodes[0])
                return None

        if isinstance(type_ref, (ObjectType, InterfaceType, UnionType)):
            object_type = self._resolve_concrete_type(type_ref, result, field_nodes, path)
            if object_type is None:
                return None
            subfields = self._collect_subfields(object_type, field_nodes)
            try:
                return await self._execute_fields(
                    object_type, result, subfields, path, serial=False
                )
            except _NullBubble:
                return None  # bubble stops here; NonNull wrapper re-raises if needed

        return None

    async def _complete_list(self, type_ref, field_nodes, path, result, info):
        if isinstance(result, (str, bytes)) or not hasattr(result, "__iter__"):
            self._record(
                GraphQLError(
                    f"Expected a list for field {field_nodes[0].name.value!r}."
                ),
                path,
                field_nodes[0],
            )
            return None

        of_type = type_ref.of_type
        items = list(result)

        async def complete_item(index, item):
            try:
                return await self._complete_value(
                    of_type, field_nodes, path + [index], item, info
                )
            except _NullBubble:
                return _BUBBLE

        completed = await asyncio.gather(
            *(complete_item(i, item) for i, item in enumerate(items))
        )
        out = []
        bubbled = False
        for value in completed:
            if value is _BUBBLE:
                bubbled = True
                out.append(None)
            else:
                out.append(value)
        if bubbled:
            raise _NullBubble()
        return out

    def _resolve_concrete_type(self, named, value, field_nodes, path):
        if isinstance(named, ObjectType):
            return named
        runtime = None
        resolver = getattr(named, "resolve_type", None)
        if resolver is not None:
            resolved = resolver(value)
            runtime = (
                self.schema.type_map.get(resolved)
                if isinstance(resolved, str)
                else resolved
            )
        if runtime is None:
            inferred = getattr(type(value), "__fastql_type__", None)
            if isinstance(inferred, ObjectType):
                runtime = self.schema.type_map.get(inferred.name, inferred)
        elif isinstance(runtime, ObjectType):
            runtime = self.schema.type_map.get(runtime.name, runtime)
        if not isinstance(runtime, ObjectType):
            self._record(
                GraphQLError(
                    f"Could not resolve a concrete object type for {named.name!r}."
                ),
                path,
                field_nodes[0],
            )
            return None
        return runtime

    def _collect_subfields(self, object_type, field_nodes):
        merged: dict[str, list[ast.FieldNode]] = {}
        for node in field_nodes:
            if node.selection_set is None:
                continue
            sub = collect_fields(
                self.schema, object_type, node.selection_set,
                self.variable_values, self.fragments,
            )
            for key, nodes in sub.items():
                merged.setdefault(key, []).extend(nodes)
        return merged

    # -- resolver invocation --------------------------------------------------

    async def _resolve_field(self, field_def, source, args, info):
        owner = getattr(field_def, "owner", None)
        resolution_source = source
        if owner is not None:
            resolution_source = await self._root_instance(owner)
            info.root_value = resolution_source

        async def core(current_source, current_info, **current_args):
            resolver = field_def.resolver
            if resolver is None:
                result = _default_resolve(
                    current_source,
                    getattr(field_def, "python_name", None) or current_info.field_name,
                )
                if inspect.isawaitable(result):
                    result = await result
                return result
            if owner is not None:
                resolver = resolver.__get__(current_source, owner)
            return await self._invoke(resolver, current_source, current_args, current_info)

        for permission_value in getattr(field_def, "permission_classes", []):
            permission = (
                permission_value()
                if isinstance(permission_value, type)
                else permission_value
            )
            allowed = permission.has_permission(resolution_source, info, **args)
            if inspect.isawaitable(allowed):
                allowed = await allowed
            if not allowed:
                raise GraphQLError(
                    getattr(permission, "message", "Permission denied")
                )

        next_ = core
        for extension_value in reversed(getattr(field_def, "extensions", [])):
            extension = (
                extension_value() if isinstance(extension_value, type) else extension_value
            )
            previous = next_

            async def wrapped(
                current_source,
                current_info,
                _extension=extension,
                _next=previous,
                **current_args,
            ):
                result = _extension.resolve(
                    _next, current_source, current_info, **current_args
                )
                if inspect.isawaitable(result):
                    result = await result
                return result

            next_ = wrapped

        for schema_ext in reversed(self.resolve_extensions):
            previous = next_

            async def schema_wrapped(
                current_source,
                current_info,
                _extension=schema_ext,
                _next=previous,
                **current_args,
            ):
                result = _extension.resolve(
                    _next, current_source, current_info, **current_args
                )
                if inspect.isawaitable(result):
                    result = await result
                return result

            next_ = schema_wrapped
        return await next_(resolution_source, info, **args)

    async def _invoke(self, resolver, source, args, info):
        plan = _injection_plan(resolver)
        kwargs: dict[str, Any] = {}
        for binding in plan:
            role = binding.role
            if role == "arg":
                if binding.name in args:
                    kwargs[binding.name] = args[binding.name]
            elif role == "parent":
                kwargs[binding.name] = source
            elif role == "context":
                kwargs[binding.name] = self.context
            elif role == "info":
                kwargs[binding.name] = info
            elif role == "dependency":
                kwargs[binding.name] = await self._dependency_value(binding)
        result = resolver(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def _dependency_value(self, binding):
        key = binding.dependency_type or binding.provider
        value = self.dependency_values.get(key, _MISSING_DEPENDENCY)
        if value is _MISSING_DEPENDENCY:
            value = binding.provider(self.context)
            if inspect.isawaitable(value):
                value = asyncio.ensure_future(value)
            self.dependency_values[key] = value
        if inspect.isawaitable(value):
            resolved = await value
            self.dependency_values[key] = resolved
            return resolved
        return value

    async def _root_instance(self, owner):
        existing = self.root_instances.get(owner)
        if existing is not None:
            if inspect.isawaitable(existing):
                return await existing
            return existing
        task = asyncio.create_task(self._create_root_instance(owner))
        self.root_instances[owner] = task
        instance = await task
        self.root_instances[owner] = instance
        return instance

    async def _create_root_instance(self, owner):
        kwargs = {}
        for binding in build_injection_plan(owner):
            if binding.role == "context":
                kwargs[binding.name] = self.context
            elif binding.role == "dependency":
                kwargs[binding.name] = await self._dependency_value(binding)
            elif binding.role == "arg":
                raise TypeError(
                    f"Root container {owner.__name__} constructor parameter "
                    f"{binding.name!r} must be Context or a registered dependency"
                )
        return owner(**kwargs)

    # -- errors ---------------------------------------------------------------

    def _record(self, error: GraphQLError, path, node) -> None:
        if error.path is None:
            error.path = list(path)
        if not error.locations:
            loc = getattr(node, "loc", None)
            if loc is not None:
                from fastql.language.source import get_location

                error.locations = [get_location(loc.source, loc.start)]
        self.errors.append(error)


def _default_resolve(source, field_name):
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _injection_plan(resolver):
    """Return the cached injection plan for ``resolver``.

    Built lazily at execution time (after all dependency providers are
    registered) and cached per resolver.
    """
    return build_injection_plan(resolver)


_MISSING_DEPENDENCY = object()


__all__ = ["execute", "ExecutionResult", "Info", "ResolveInfo"]
