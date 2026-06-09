"""Compile registered decorator definitions into a validated :class:`Schema`.

``build_schema`` assembles the root operation types (from explicitly provided
roots and/or the registered ``@Query`` / ``@Mutation`` / ``@Subscription``
operations), walks the reachable type graph resolving every forward/circular
reference thunk in place, includes explicitly listed unreachable types, and
validates completeness (unknown references, duplicate names, unsatisfied
interfaces, non-object union members).
"""

from __future__ import annotations

import copy
import re
from typing import Any, TypeVar

from fastql.decorators.annotations import (
    GenericTypeReference,
    TypeReference,
    TypeVarRef,
    resolve_type_hint,
)
from fastql.decorators.registry import DecoratorRegistry, default_registry
from fastql.errors import GraphQLError
from fastql.types import (
    EnumType,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    Schema,
    SchemaConfig,
    Boolean,
    Float,
    ID,
    Int,
    String,
    UnionType,
)
from fastql.types.schema import default_directives
from fastql.types.wrappers import ListType, NonNull

_ROOT_DEFAULT_NAMES = {
    "query": "Query",
    "mutation": "Mutation",
    "subscription": "Subscription",
}

_NAMED_TYPES = (
    ScalarType,
    ObjectType,
    InterfaceType,
    UnionType,
    EnumType,
    InputObjectType,
)


class SchemaBuildError(GraphQLError):
    """Raised when a schema cannot be assembled or fails completeness checks."""


def build_schema(
    query: Any = None,
    *,
    mutation: Any = None,
    subscription: Any = None,
    types: list[Any] | None = None,
    registry: DecoratorRegistry | None = None,
    config: SchemaConfig | None = None,
    extensions: list[Any] | None = None,
) -> Schema:
    """Build a :class:`Schema` from decorated definitions.

    ``query`` / ``mutation`` / ``subscription`` may each be an ``ObjectType``, a
    class decorated with ``@Type``, or ``None`` to assemble the root purely from
    the registry's operations. ``types`` lists extra types to include even when
    unreachable from the roots.
    """
    selected_config = config or SchemaConfig()
    prepared = _prepare_registry(registry or default_registry, selected_config)
    return _SchemaBuilder(prepared, selected_config).build(
        query, mutation, subscription, list(types or []), list(extensions or [])
    )


class _SchemaBuilder:
    def __init__(self, registry: DecoratorRegistry, config: SchemaConfig) -> None:
        self.registry = registry
        self.config = config
        self.by_name: dict[str, Any] = {}
        self.visited: set[int] = set()
        self.object_types: list[ObjectType] = []
        #: Synthesized concrete generic types, keyed by their synthetic name.
        self._generic_cache: dict[str, Any] = {}
        # Index decorated definitions by their Python class name so forward
        # references resolve through the registry regardless of where the class
        # was defined (module level, nested, or inside a function).
        self._python_name_index: dict[str, Any] = {
            getattr(cls, "__name__", None): ir
            for cls, ir in registry.types_by_python.items()
        }

    def build(
        self, query: Any, mutation: Any, subscription: Any, extra_types: list[Any],
        extensions: list[Any] | None = None,
    ) -> Schema:
        query_root = self._root("query", query)
        if query_root is None:
            raise SchemaBuildError("Schema must define a query root type.")
        if not query_root.fields:
            raise SchemaBuildError("Query root type must define at least one field.")
        self._add_introspection_fields(query_root)
        mutation_root = self._root("mutation", mutation)
        subscription_root = self._root("subscription", subscription)

        extra_ir = [self._as_named_type(t) for t in extra_types]

        for root in (query_root, mutation_root, subscription_root, *extra_ir):
            if root is not None:
                self._resolve_named(root)

        self._validate_interfaces()

        directives = self._collect_directives()
        self._validate_applied_directives(directives)

        return Schema(
            query=query_root,
            mutation=mutation_root,
            subscription=subscription_root,
            types=extra_ir,
            config=self.config,
            extensions=list(extensions or []),
            directives=directives,
            _built=True,
        )

    # -- root assembly --------------------------------------------------------

    def _root(self, kind: str, provided: Any) -> ObjectType | None:
        base = self._resolve_root_input(provided)
        op_fields = {
            name: definition.field
            for name, definition in self.registry.operations.get(kind, {}).items()
        }

        explicit_root = (
            isinstance(provided, type)
            and provided in self.registry.root_types_by_python
        )
        if explicit_root:
            return base
        if base is None and not op_fields:
            return None
        if op_fields and base is None:
            return ObjectType(_ROOT_DEFAULT_NAMES[kind], fields=dict(op_fields))
        if not op_fields:
            return base  # use the provided root as-is

        # Merge registered operations into the provided root's fields.
        fields = dict(base.fields)
        for fname, ffield in op_fields.items():
            if fname in fields:
                raise SchemaBuildError(
                    f"Duplicate field {fname!r} on the {base.name} root type."
                )
            fields[fname] = ffield
        return ObjectType(
            base.name,
            fields=fields,
            interfaces=list(base.interfaces),
            description=base.description,
        )

    def _add_introspection_fields(self, query_root: ObjectType) -> None:
        from fastql.introspection import introspection_root_fields

        for name, field_def in introspection_root_fields().items():
            query_root.fields.setdefault(name, field_def)

    def _resolve_root_input(self, provided: Any) -> ObjectType | None:
        if provided is None:
            return None
        if isinstance(provided, ObjectType):
            return provided
        registered_root = self.registry.root_types_by_python.get(provided)
        if registered_root is not None:
            return registered_root
        registered_type = self.registry.types_by_python.get(provided)
        if isinstance(registered_type, ObjectType):
            return registered_type
        ir = getattr(provided, "__fastql_type__", None)
        if isinstance(ir, ObjectType):
            return ir
        raise SchemaBuildError(
            f"{provided!r} is not a GraphQL object type usable as a root."
        )

    def _as_named_type(self, value: Any) -> Any:
        if isinstance(value, _NAMED_TYPES):
            return value
        ir = self.registry.types_by_python.get(value)
        if ir is None:
            ir = getattr(value, "__fastql_type__", None)
        if ir is not None:
            return ir
        raise SchemaBuildError(f"{value!r} is not a registered GraphQL type.")

    # -- graph walk + thunk resolution ---------------------------------------

    def _resolve_named(self, type_: Any) -> None:
        if id(type_) in self.visited:
            return
        existing = self.by_name.get(type_.name)
        if existing is not None and existing is not type_:
            raise SchemaBuildError(f"Duplicate type name: {type_.name}")
        self.by_name[type_.name] = type_
        self.visited.add(id(type_))

        if isinstance(type_, (ObjectType, InterfaceType)):
            if isinstance(type_, ObjectType):
                self.object_types.append(type_)
                for interface in type_.interfaces:
                    self._resolve_named(interface)
            for field_name, field_def in type_.fields.items():
                where = f"{type_.name}.{field_name}"
                field_def.type = self._resolve_ref(field_def.type, where)
                for arg_name, arg in field_def.args.items():
                    arg.type = self._resolve_ref(arg.type, f"{where}({arg_name}:)")
                    self._enqueue(arg.type)
                self._enqueue(field_def.type)
        elif isinstance(type_, UnionType):
            resolved_members = []
            for member in type_.types:
                resolved = self._resolve_ref(member, f"union {type_.name}")
                if not isinstance(resolved, ObjectType):
                    raise SchemaBuildError(
                        f"Union {type_.name!r} member must be an object type, "
                        f"got {resolved!r}."
                    )
                resolved_members.append(resolved)
                self._resolve_named(resolved)
            type_.types = resolved_members
        elif isinstance(type_, InputObjectType):
            for field_name, input_field in type_.fields.items():
                where = f"{type_.name}.{field_name}"
                input_field.type = self._resolve_ref(input_field.type, where)
                self._enqueue(input_field.type)

    def _resolve_ref(self, ref: Any, where: str) -> Any:
        if isinstance(ref, NonNull):
            return NonNull(self._resolve_ref(ref.of_type, where))
        if isinstance(ref, ListType):
            return ListType(self._resolve_ref(ref.of_type, where))
        if isinstance(ref, GenericTypeReference):
            return self._resolve_ref(self._synthesize_generic(ref, where), where)
        if isinstance(ref, TypeReference):
            resolved = self._lookup_reference(ref)
            if resolved is None:
                raise SchemaBuildError(
                    f"Unknown type {ref.name!r} referenced by {where}."
                )
            return self._resolve_ref(resolved, where)
        if isinstance(ref, _NAMED_TYPES):
            replacement = self.registry.types_by_name.get(ref.name)
            if replacement is not None:
                return replacement
        # A decorated class used directly as a type reference.
        if not isinstance(ref, _NAMED_TYPES):
            ir = getattr(ref, "__fastql_type__", None)
            if ir is not None:
                return ir
        return ref

    def _lookup_reference(self, ref: TypeReference) -> Any:
        """Resolve a forward reference via the registry, then module globals."""
        ir = self._python_name_index.get(ref.name)
        if ir is not None:
            return ir
        ir = self.registry.types_by_name.get(ref.name)
        if ir is not None:
            return ir
        try:
            return ref()
        except LookupError:
            return None

    def _enqueue(self, type_ref: Any) -> None:
        named = _unwrap(type_ref)
        if isinstance(named, _NAMED_TYPES):
            self._resolve_named(named)

    # -- generic type synthesis ----------------------------------------------

    def _synthesize_generic(self, ref: GenericTypeReference, where: str) -> Any:
        """Concretize ``Template[args]`` into a named type, one per parametrization."""
        template = ref.template
        arg_types = [self._named_for_arg(arg, ref.module, where) for arg in ref.args]
        name = self._generic_name(template, arg_types)

        cached = self._generic_cache.get(name) or self.registry.types_by_name.get(name)
        if cached is not None:
            return cached

        mapping = dict(zip(template.type_param_names, arg_types))
        own_fields = {
            field_name: self._concretize_field(field_def, mapping)
            for field_name, field_def in template.fields.items()
        }

        if template.kind == "interface":
            concrete: Any = InterfaceType(
                name, fields=own_fields, description=template.description
            )
        elif template.kind == "input":
            concrete = InputObjectType(
                name,
                fields=own_fields,
                description=template.description,
                python_type=template.python_type,
            )
        else:
            interfaces = [
                self._resolve_ref(self._as_named_type(value), where)
                for value in template.interfaces
            ]
            merged: dict[str, Any] = {}
            for interface in interfaces:
                merged.update(interface.fields)
            merged.update(own_fields)
            concrete = ObjectType(
                name,
                fields=merged,
                interfaces=interfaces,
                description=template.description,
            )

        # Synthesis happens after the registry-wide naming pass, so apply field
        # name conversion to the freshly built type here.
        if self.config.auto_camel_case:
            _apply_naming(concrete, set())

        # Memoize before resolving so a self-referential generic terminates.
        self._generic_cache[name] = concrete
        self.registry.types_by_name[name] = concrete
        return concrete

    def _named_for_arg(self, arg: Any, module: str | None, where: str) -> Any:
        if isinstance(arg, (*_NAMED_TYPES, TypeReference)):
            named = arg  # already an IR type (e.g. bound from a nested generic)
        else:
            named = _unwrap(resolve_type_hint(arg, module=module))
        return self._resolve_ref(named, f"{where} (generic argument)")

    def _generic_name(self, template: Any, arg_types: list[Any]) -> str:
        arg_names = [getattr(named, "name", None) or "Unknown" for named in arg_types]
        if template.name_template:
            return template.name_template.format(
                **dict(zip(template.type_param_names, arg_names))
            )
        return "".join(arg_names) + template.base_name

    def _concretize_field(self, field_def: Any, mapping: dict[str, Any]) -> Any:
        new_field = copy.copy(field_def)
        new_field.type = _substitute_typevars(field_def.type, mapping)
        if getattr(field_def, "args", None):
            new_args = {}
            for arg_name, arg in field_def.args.items():
                new_arg = copy.copy(arg)
                new_arg.type = _substitute_typevars(arg.type, mapping)
                new_args[arg_name] = new_arg
            new_field.args = new_args
        return new_field

    # -- validation -----------------------------------------------------------

    def _validate_interfaces(self) -> None:
        for obj in self.object_types:
            for interface in obj.interfaces:
                for field_name in interface.fields:
                    if field_name not in obj.fields:
                        raise SchemaBuildError(
                            f"Type {obj.name!r} must implement field "
                            f"{field_name!r} from interface {interface.name!r}."
                        )

    # -- custom directives ----------------------------------------------------

    def _collect_directives(self) -> dict[str, Any]:
        """Merge the built-in directives with any author-defined ones."""
        merged = dict(default_directives())
        merged.update(self.registry.directives)
        return merged

    def _validate_applied_directives(self, known: dict[str, Any]) -> None:
        """Check applied-directive locations and coerce their arguments."""
        _LOCATION = {
            ObjectType: "OBJECT",
            InterfaceType: "INTERFACE",
            UnionType: "UNION",
            EnumType: "ENUM",
            ScalarType: "SCALAR",
            InputObjectType: "INPUT_OBJECT",
        }
        for type_ in self.by_name.values():
            location = _LOCATION.get(type(type_))
            if location is not None:
                self._check_directives(
                    getattr(type_, "directives", []), location, known, type_.name
                )
            if isinstance(type_, (ObjectType, InterfaceType)):
                for field_name, field_def in type_.fields.items():
                    where = f"{type_.name}.{field_name}"
                    self._check_directives(
                        field_def.directives, "FIELD_DEFINITION", known, where
                    )
                    for arg_name, arg in field_def.args.items():
                        self._check_directives(
                            getattr(arg, "directives", []),
                            "ARGUMENT_DEFINITION",
                            known,
                            f"{where}({arg_name}:)",
                        )
            elif isinstance(type_, InputObjectType):
                for field_name, input_field in type_.fields.items():
                    self._check_directives(
                        getattr(input_field, "directives", []),
                        "INPUT_FIELD_DEFINITION",
                        known,
                        f"{type_.name}.{field_name}",
                    )

    def _check_directives(
        self, applied: list, location: str, known: dict[str, Any], where: str
    ) -> None:
        from fastql.execution.values import coerce_input_value

        for directive in applied:
            definition = known.get(directive.name)
            if definition is None:
                continue  # unknown/federation directives pass through unchecked
            if location not in definition.locations:
                raise SchemaBuildError(
                    f"Directive @{directive.name} is not allowed on {location} "
                    f"(applied to {where}); valid locations: "
                    f"{', '.join(definition.locations)}."
                )
            for arg_name, value in (directive.arguments or {}).items():
                if arg_name not in definition.args:
                    raise SchemaBuildError(
                        f"Unknown argument {arg_name!r} for directive "
                        f"@{directive.name} on {where}."
                    )
                try:
                    coerce_input_value(
                        value,
                        definition.args[arg_name].type,
                        f"@{directive.name}({arg_name}:)",
                    )
                except GraphQLError as error:
                    raise SchemaBuildError(str(error))


def _unwrap(type_ref: Any) -> Any:
    while isinstance(type_ref, (NonNull, ListType)):
        type_ref = type_ref.of_type
    return type_ref


def _substitute_typevars(ref: Any, mapping: dict[str, Any]) -> Any:
    """Replace :class:`TypeVarRef` placeholders with their bound named types.

    Also descends into a nested :class:`GenericTypeReference` (e.g. ``Edge[T]``
    inside ``Connection[T]``), binding its type-variable arguments.
    """
    if isinstance(ref, NonNull):
        return NonNull(_substitute_typevars(ref.of_type, mapping))
    if isinstance(ref, ListType):
        return ListType(_substitute_typevars(ref.of_type, mapping))
    if isinstance(ref, TypeVarRef):
        bound = mapping.get(ref.name)
        if bound is None:
            raise SchemaBuildError(
                f"Unbound type variable {ref.name!r} in a generic type."
            )
        return bound
    if isinstance(ref, GenericTypeReference):
        new_args = tuple(_bind_generic_arg(arg, mapping) for arg in ref.args)
        return GenericTypeReference(ref.template, new_args, ref.module)
    return ref


def _bind_generic_arg(arg: Any, mapping: dict[str, Any]) -> Any:
    """Bind a nested generic's argument when it is one of the outer type vars."""
    if isinstance(arg, TypeVar):
        return mapping.get(arg.__name__, arg)
    if isinstance(arg, str):
        return mapping.get(arg, arg)
    return arg


def _prepare_registry(
    registry: DecoratorRegistry, config: SchemaConfig
) -> DecoratorRegistry:
    scalar_memo = {
        id(scalar): scalar for scalar in (Int, Float, String, Boolean, ID)
    }
    prepared = copy.deepcopy(registry, scalar_memo)
    if not config.auto_camel_case:
        return prepared
    seen: set[int] = set()
    for type_ in [
        *prepared.types_by_python.values(),
        *prepared.root_types_by_python.values(),
    ]:
        _apply_naming(type_, seen)
    for kind, definitions in prepared.operations.items():
        renamed = {}
        for old_name, definition in definitions.items():
            field_def = definition.field
            new_name = _configured_name(old_name, field_def)
            if new_name in renamed:
                raise SchemaBuildError(
                    f"Duplicate {kind} field {new_name!r} after name conversion."
                )
            definition.name = new_name
            renamed[new_name] = definition
        prepared.operations[kind] = renamed
    prepared.types_by_name = {
        type_.name: type_ for type_ in prepared.types_by_python.values()
    }
    return prepared


def _apply_naming(type_: Any, seen: set[int]) -> None:
    if id(type_) in seen:
        return
    seen.add(id(type_))
    fields = getattr(type_, "fields", None)
    if not isinstance(fields, dict):
        return
    renamed = {}
    for old_name, field_def in fields.items():
        new_name = _configured_name(old_name, field_def)
        if new_name in renamed:
            raise SchemaBuildError(
                f"Duplicate field {new_name!r} on {type_.name!r} after name conversion."
            )
        if hasattr(field_def, "args"):
            args = {}
            for old_arg_name, arg in field_def.args.items():
                new_arg_name = _configured_name(old_arg_name, arg)
                if new_arg_name in args:
                    raise SchemaBuildError(
                        f"Duplicate argument {new_arg_name!r} on {type_.name}.{new_name}."
                    )
                args[new_arg_name] = arg
            field_def.args = args
        renamed[new_name] = field_def
    type_.fields = renamed


def _configured_name(current: str, definition: Any) -> str:
    if getattr(definition, "graphql_name_explicit", False):
        return current
    return _camel_case(getattr(definition, "python_name", None) or current)


def _camel_case(value: str) -> str:
    return re.sub(r"_+([a-zA-Z0-9])", lambda match: match.group(1).upper(), value)


__all__ = ["build_schema", "SchemaBuildError"]
