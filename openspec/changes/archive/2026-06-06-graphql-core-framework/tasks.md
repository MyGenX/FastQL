## 1. Project setup

- [x] 1.1 Create `pyproject.toml` for package `fastql` (Python 3.11+, zero runtime deps, dev deps `pytest` + `pytest-asyncio`, async test mode enabled)
- [x] 1.2 Create the `fastql/` package skeleton and subpackages (`language/`, `types/`, `decorators/`, `validation/`, `execution/`) with empty `__init__.py` files
- [x] 1.3 Create the `tests/` directory and a smoke test asserting `import fastql` succeeds

## 2. Language front-end (capability: language-parsing)

- [x] 2.1 Implement `language/source.py`: `Source(body, name)` and `SourceLocation` (line/column from offset)
- [x] 2.2 Implement `language/ast.py`: node classes for `Document`, `OperationDefinition`, `SelectionSet`, `Field`, `Argument`, `FragmentDefinition`, `FragmentSpread`, `InlineFragment`, `VariableDefinition`, `Directive`, value nodes, and type-reference nodes, each carrying a location
- [x] 2.3 Implement `language/lexer.py`: tokenize names, int/float literals, single-line and block strings, and all punctuators; skip commas/whitespace/comments; raise located syntax errors on invalid characters
- [x] 2.4 Implement `language/parser.py`: recursive-descent parser producing the `Document` AST with located syntax errors on unexpected tokens
- [x] 2.5 Implement `language/printer.py`: AST → string for debugging
- [x] 2.6 Tests: lexer token streams, parser ASTs for queries/mutations/variables/fragments, and syntax-error locations (covers all language-parsing scenarios)

## 3. Type-system IR (capability: type-system)

- [x] 3.1 Implement `types/wrappers.py`: `NonNull` and `ListType` wrapping types
- [x] 3.2 Implement `types/definition.py`: `ObjectType`, `InterfaceType`, `UnionType`, `EnumType`, `InputObjectType`, `Field`, `Argument`, `InputField`, and directive definitions
- [x] 3.3 Implement `types/scalars.py`: built-in `Int`, `Float`, `String`, `Boolean`, `ID` with serialize / parse-value / parse-literal, raising typed errors on invalid coercion
- [x] 3.4 Implement `types/schema.py`: `Schema` with root types, reachable type map, and directive definitions
- [x] 3.5 Tests: object/field/argument IR shape, wrapping-type nesting order, scalar serialization/coercion (incl. invalid `Int`, `ID` string/int), and reachable type-map construction

## 4. Decorator authoring surface (capability: schema-definition)

- [x] 4.1 Implement `decorators/field.py`: the `Field(...)` descriptor and `@Field` method decorator (name/description/deprecation/type overrides; computed fields)
- [x] 4.2 Implement `decorators/annotations.py`: Python type-hint → IR resolver (`int/float/str/bool/ID`, `X | None`/`Optional`, `list[X]`, `Enum`, registered types, and string forward refs stored as thunks; bare hints → `NonNull`)
- [x] 4.3 Implement `decorators/object.py`: `@Type`, `@Input`, `@Interface` (introspect annotated attributes and `Field()` defaults; record interface implementation)
- [x] 4.4 Implement `decorators/enum.py` and `decorators/union.py`: `@Enum` (wrap Python `Enum`) and `@Union` (over registered object types)
- [x] 4.5 Implement `decorators/scalar.py`: `@Scalar` custom-scalar registration (serialize/parse)
- [x] 4.6 Implement `decorators/operations.py`: `@Query`, `@Mutation`, `@Subscription` (register root fields; derive args from parameters excluding injected ones; field type from return hint)
- [x] 4.7 Tests: each decorator registers the expected definition, hint inference (optional/list/forward ref), `Field()` overrides, computed fields, and operation arg derivation (covers schema-definition scenarios)

## 5. Registry and schema building (capability: schema-building)

- [x] 5.1 Implement `registry.py`: `TypeRegistry` collecting decorated definitions and holding unresolved thunks
- [x] 5.2 Implement `schema_builder.py`: `build_schema(query=, mutation=, subscription=, types=[...])` — resolve all thunks/forward refs and include explicitly listed unreachable types
- [x] 5.3 Add build-time completeness validation: unresolved type reference, duplicate type name, unsatisfied interface, non-object union member — each raising a descriptive error
- [x] 5.4 Tests: build from a query root, circular references resolved, explicitly-included type present, and each completeness-error scenario

## 6. Query validation (capability: query-validation)

- [x] 6.1 Implement `validation/rules.py` with the must-have rules: field exists on parent type, argument defined and correctly typed, fragment target type exists and is compatible, variable defined and used consistently
- [x] 6.2 Implement a `validate(schema, document)` entry returning a list of located validation errors (empty when valid)
- [x] 6.3 Tests: unknown field, unknown argument, undefined variable, and a fully valid operation (covers query-validation scenarios)

## 7. Execution engine (capability: query-execution)

- [x] 7.1 Implement `execution/collect_fields.py`: field collection honoring fragments, inline fragments, and `@skip`/`@include`
- [x] 7.2 Implement `execution/values.py`: input coercion (arguments + variables) and output result coercion, reusing the scalar coercion logic
- [x] 7.3 Implement `execution/execute.py`: async `execute(schema, query, variable_values, context, operation_name)` — parse (if string), validate, select operation, resolve fields concurrently via `asyncio.gather`, and return `ExecutionResult{data, errors, extensions}`
- [x] 7.4 Support mixed `async def` / `def` resolvers (classify once per resolver)
- [x] 7.5 Implement error handling and null propagation: capture `GraphQLError` with path/location, null the field, propagate null to the nearest nullable ancestor, and keep resolving unaffected fields
- [x] 7.6 Tests: successful query, operation selection by name, parse failure result, sync+async mix, `@skip`, argument coercion via variable, resolver error on a nullable field, and null propagation through a non-null field

## 8. Context and dependency injection (capability: context-injection)

- [x] 8.1 Implement `context.py`: the `Context` object and a per-resolver injection plan derived from `inspect.signature` + annotations (cached per resolver)
- [x] 8.2 Bind parameters by role: GraphQL argument by name, parent/source object, resolve `info`, and `Context`; pass only declared parameters
- [x] 8.3 Implement dependency-provider registration and resolution from the active context (e.g. `CurrentUser`)
- [x] 8.4 Wire injection into the executor's resolver invocation path
- [x] 8.5 Tests: arg + context injected together, info injection, context value reaches resolvers, omitted context not passed, and a registered dependency resolved from context

## 9. Introspection (capability: introspection)

- [x] 9.1 Implement `introspection.py`: the introspection type graph and `__schema` / `__type(name:)` root meta-fields
- [x] 9.2 Implement `__typename` resolution on object/interface/union types
- [x] 9.3 Wire introspection meta-fields into `build_schema`/the executor
- [x] 9.4 Tests: `{ __schema { types { name kind } } }`, `{ __type(name: "User") { name fields { name } } }`, and `__typename` in a selection

## 10. Public API and end-to-end integration

- [x] 10.1 Implement `errors.py`: `GraphQLError`, `GraphQLSyntaxError`, `ValidationError` with message/locations/path
- [x] 10.2 Implement `fastql/__init__.py` exporting decorators, `Field`, `Context`, built-in scalars, `build_schema`, and `execute`
- [x] 10.3 Add an end-to-end example (`@Type User`, `@Query user(id, ctx)`) and an integration test that parses, validates, injects args+context, executes async, and asserts the spec-shaped `{data, errors}`
- [x] 10.4 Add a `README` quickstart showing the primitive decorator usage and the framework-agnostic `execute` entry point
- [x] 10.5 Run the full `pytest` suite and confirm all capability scenarios pass
