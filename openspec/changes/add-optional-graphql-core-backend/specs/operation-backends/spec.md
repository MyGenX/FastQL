## ADDED Requirements

### Requirement: Select one operation backend per schema

FastQL SHALL define a public `OperationBackend` contract and SHALL select exactly one backend for each schema. `SchemaConfig.operation_backend` SHALL accept `"fastql"`, `"graphql-core"`, or a compatible backend object and SHALL default to `"fastql"`. The selected backend SHALL consistently own parsing, operation inspection, validation, query/mutation execution, and subscriptions for that schema.

#### Scenario: Default backend

- **WHEN** a schema is constructed without specifying `operation_backend`
- **THEN** it uses the existing FastQL parser, AST, validator, executor, subscriptions, and incremental delivery

#### Scenario: GraphQL-core shortcut

- **WHEN** a schema is configured with `operation_backend="graphql-core"` and the optional extra is installed
- **THEN** it uses a default `GraphQLCoreBackend` for every operation path

#### Scenario: Configured backend object

- **WHEN** a schema receives a compatible `OperationBackend` object
- **THEN** FastQL stores and uses that object without switching backends per request

#### Scenario: Invalid backend configuration

- **WHEN** a schema receives an unknown backend name or an object that does not satisfy the backend contract
- **THEN** schema construction raises an actionable `ValueError`

### Requirement: Delegate a native GraphQL-core operation pipeline

The optional `GraphQLCoreBackend` SHALL compile the FastQL schema to a native GraphQL-core `GraphQLSchema` and SHALL use native GraphQL-core 3.2 source, AST, parsing, validation, query/mutation execution, subscription execution, middleware, visitors, and schema utilities. It SHALL NOT pass GraphQL-core documents through FastQL validation or field execution.

#### Scenario: Native query execution

- **WHEN** a GraphQL-core-backed schema executes a query string
- **THEN** GraphQL-core parses, validates, and executes its native document and FastQL returns a normalized result

#### Scenario: Native middleware and validation rules

- **WHEN** `GraphQLCoreBackend` is configured with middleware or custom validation rules
- **THEN** those native GraphQL-core hooks run in the configured operation pipeline

#### Scenario: Native integration utilities

- **WHEN** a user imports GraphQL-core parsing, validation, visitor, printer, or schema utilities from `fastql.integrations.graphql_core`
- **THEN** those utilities operate on native GraphQL-core values without changing `fastql.parse()` or `fastql.language`

### Requirement: Compile and expose a cached native schema

The GraphQL-core integration SHALL convert FastQL scalar, enum, object, interface, union, input-object, wrapper, root, directive, description, default, deprecation, abstract-type, custom-scalar, upload, federation, and resolver metadata into a native `GraphQLSchema`. Compilation SHALL be lazy and cached per FastQL schema, and public APIs SHALL expose compilation, cached access, invalidation, and explicit rebuilding.

#### Scenario: Recursive schema conversion

- **WHEN** FastQL types contain forward, circular, interface, union, or input-object references
- **THEN** native schema compilation resolves them to one consistent GraphQL-core type graph

#### Scenario: Cached schema reused

- **WHEN** multiple GraphQL-core operations execute against an unchanged FastQL schema
- **THEN** they reuse the same compiled native schema instance

#### Scenario: Cache explicitly rebuilt

- **WHEN** a user invalidates the compiled schema or requests `rebuild=True`
- **THEN** the next access creates a new native schema reflecting the current FastQL IR

#### Scenario: Native schema available to tooling

- **WHEN** a user calls the supported conversion/access API
- **THEN** it returns the cached native `GraphQLSchema` for GraphQL-core tooling and middleware

### Requirement: Preserve FastQL resolver contracts

GraphQL-core-backed fields SHALL preserve FastQL resolver argument naming, dependency injection, original user context, `Info`, root/container instantiation, permissions, field extensions, schema resolve extensions, sync/async interoperability, custom scalars, input-object construction, default factories, abstract type resolution, uploads, and error masking. Native GraphQL-core middleware SHALL wrap the adapted FastQL field resolver.

#### Scenario: Dependency-injected resolver

- **WHEN** a GraphQL-core-backed field resolver requests GraphQL arguments, parent, context, `Info`, and a registered dependency
- **THEN** it receives the same FastQL-facing values and Python argument names as under the FastQL backend

#### Scenario: Permission and extension ordering

- **WHEN** native middleware, FastQL permissions, field extensions, schema extensions, and a user resolver apply to one field
- **THEN** native middleware is outermost and the existing FastQL permission/extension/resolver ordering is preserved inside it

#### Scenario: Custom scalar literal

- **WHEN** GraphQL-core coerces a literal for a FastQL custom scalar
- **THEN** the existing FastQL `parse_literal` hook receives an equivalent FastQL value node at the scalar boundary

#### Scenario: Input object and Python names

- **WHEN** an input object uses renamed fields, a Python class, defaults, or default factories
- **THEN** GraphQL-core coercion produces the same Python-facing input shape expected by the FastQL resolver

#### Scenario: Subscription resolver

- **WHEN** a GraphQL-core-backed subscription root resolver returns an async iterator
- **THEN** FastQL dependency injection initializes the stream and GraphQL-core executes each yielded event through the native selection set

### Requirement: Normalize backend results and errors

Every backend SHALL return FastQL `ExecutionResult` and `GraphQLError` contracts at public execution boundaries. GraphQL-core normalization SHALL preserve data, partial data, extensions, message, locations, path, and original errors where available; parse/validation failures SHALL be unexecuted, runtime field failures SHALL be executed, and FastQL masking and lifecycle-extension result merging SHALL remain effective.

#### Scenario: GraphQL-core validation error

- **WHEN** native GraphQL-core validation rejects a document
- **THEN** FastQL returns an unexecuted result containing normalized located errors

#### Scenario: Partial runtime data

- **WHEN** one GraphQL-core-executed nullable field fails while siblings succeed
- **THEN** FastQL returns partial data and a normalized error with path and location

#### Scenario: Unexpected error masking

- **WHEN** masking is enabled and an adapted resolver raises an unexpected exception
- **THEN** the client receives the mask message while the normalized error retains the original exception

#### Scenario: Lifecycle extension metadata

- **WHEN** FastQL schema extensions wrap a GraphQL-core-backed operation and return extension data
- **THEN** their phase hooks run in FastQL order and their output is merged into the normalized result

### Requirement: Enforce backend document ownership

FastQL SHALL accept pre-parsed documents only when their native type belongs to the schema's selected backend. It SHALL reject foreign documents with a normalized error and SHALL NOT convert or execute them implicitly.

#### Scenario: Native GraphQL-core document accepted

- **WHEN** a GraphQL-core-backed schema receives a native GraphQL-core `DocumentNode`
- **THEN** it validates and executes that document without converting it to FastQL AST

#### Scenario: FastQL document rejected by GraphQL-core backend

- **WHEN** a GraphQL-core-backed schema receives a FastQL `DocumentNode`
- **THEN** it returns an actionable backend-document error naming the expected document type

#### Scenario: GraphQL-core document rejected by FastQL backend

- **WHEN** a FastQL-backed schema receives a native GraphQL-core `DocumentNode`
- **THEN** it returns an actionable backend-document error and does not import GraphQL-core execution code

### Requirement: Apply configured parser limits in each backend

Each backend SHALL apply the schema's configured query token and syntactic-depth limits to string sources according to the shared FastQL limit definitions. GraphQL-core mode SHALL pass the token limit to native parsing and SHALL enforce depth through a native AST traversal before validation.

#### Scenario: GraphQL-core token limit exceeded

- **WHEN** a GraphQL-core-backed query exceeds `max_query_tokens`
- **THEN** FastQL returns a normalized syntax error before validation or execution

#### Scenario: GraphQL-core depth limit exceeded

- **WHEN** a GraphQL-core-backed document exceeds `max_query_depth`
- **THEN** FastQL returns a normalized located syntax error before validation or execution

#### Scenario: Direct native utility remains native

- **WHEN** a user calls the re-exported native GraphQL-core `parse` utility directly
- **THEN** it applies only arguments supplied to that utility and does not implicitly read a FastQL schema configuration
