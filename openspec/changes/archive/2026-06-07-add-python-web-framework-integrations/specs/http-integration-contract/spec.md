## ADDED Requirements

### Requirement: Framework-neutral HTTP execution contract

FastQL SHALL provide a dependency-free asynchronous HTTP handler that accepts a normalized request, executes against a configured schema, and returns a normalized response. Framework adapters SHALL delegate GraphQL protocol behavior to this handler rather than implementing independent execution flows.

#### Scenario: Adapter delegates a request

- **WHEN** an adapter receives a valid native HTTP request for its GraphQL route
- **THEN** it converts the request, invokes the shared handler, and converts the normalized response back to the framework response type

#### Scenario: Execution result is formatted consistently

- **WHEN** equivalent requests execute through different framework adapters
- **THEN** they produce equivalent GraphQL `data` and `errors` response bodies and transport status semantics

### Requirement: Supported GraphQL HTTP requests

The handler SHALL accept GraphQL queries from GET query parameters and from POST JSON bodies. POST bodies SHALL support `query`, `variables`, `operationName`, and `extensions`, SHALL reject invalid field types, and SHALL accept `application/json` and `application/graphql-response+json` media types.

#### Scenario: JSON POST executes

- **WHEN** a POST request contains a valid JSON GraphQL payload and a supported content type
- **THEN** the handler executes the selected operation with its variables and operation name

#### Scenario: GET query executes

- **WHEN** a GET request supplies a query and optional JSON-encoded variables and extensions
- **THEN** the handler executes the query operation

#### Scenario: Unsupported media type is rejected

- **WHEN** a POST request uses a content type not supported by the integration contract
- **THEN** the handler returns a `415` transport error without executing the schema

### Requirement: HTTP method and operation safety

The handler SHALL allow GraphQL execution only through GET and POST, SHALL reject unsupported methods with `405`, and SHALL reject mutation or subscription operations sent through GET.

#### Scenario: Mutation over GET is rejected

- **WHEN** a GET request selects a mutation operation
- **THEN** the handler returns a method error and does not invoke the mutation resolver

#### Scenario: Unsupported method is rejected

- **WHEN** a GraphQL endpoint receives a non-supported execution method
- **THEN** the response is `405` and advertises the supported methods

### Requirement: Stable error and status behavior

The handler SHALL distinguish malformed transport requests from GraphQL parse, validation, and execution results. Transport failures SHALL use an appropriate 4xx status and a structured error body; a successfully decoded GraphQL request SHALL return the formatted GraphQL result without exposing internal exception details by default.

#### Scenario: Malformed JSON fails before execution

- **WHEN** a POST request body is not valid JSON
- **THEN** the handler returns `400` and no resolver runs

#### Scenario: Resolver error remains a GraphQL result

- **WHEN** a resolver raises during a successfully decoded operation
- **THEN** the response contains the formatted GraphQL error and any permitted partial data

### Requirement: Configurable browser and schema routes

The shared integration contract SHALL support independently configurable GraphQL, GraphiQL, SDL, and introspection JSON routes. Disabled optional routes SHALL not be exposed.

#### Scenario: GraphiQL content negotiation

- **WHEN** GraphiQL is enabled and a GET without a query accepts HTML at the GraphQL route
- **THEN** the handler returns the GraphiQL document configured for that route

#### Scenario: Optional route disabled

- **WHEN** an adapter is configured without an SDL or introspection route
- **THEN** that adapter does not register or serve the disabled route

### Requirement: Host framework policy remains authoritative

FastQL adapters SHALL preserve the host framework's middleware, authentication, routing, and response lifecycle and SHALL NOT apply a global CORS, authentication, or CSRF policy on behalf of the application.

#### Scenario: Framework middleware wraps GraphQL

- **WHEN** a request passes through framework middleware before reaching the adapter
- **THEN** middleware-provided request state and authentication information remain available to the FastQL context

