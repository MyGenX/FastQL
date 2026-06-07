## ADDED Requirements

### Requirement: Start a dev server for a schema

The framework SHALL provide `serve(schema, host="127.0.0.1", port=7691, path="/graphql")` that starts a
minimal `asyncio`-based HTTP server bound to the given host and port and serving the given schema. The
default port SHALL be `7691` and the default host `127.0.0.1`, and both SHALL be overridable by the
caller. The server SHALL print a startup banner showing the base URL and the available routes, and SHALL
shut down cleanly on `KeyboardInterrupt`.

#### Scenario: Default binding

- **WHEN** `serve(schema)` is called with no host/port arguments
- **THEN** the server listens on `127.0.0.1:7691` and prints a banner with the base URL and routes

#### Scenario: Custom host and port

- **WHEN** `serve(schema, host="0.0.0.0", port=9000)` is called
- **THEN** the server listens on `0.0.0.0:9000`

#### Scenario: Graceful shutdown

- **WHEN** the server receives a `KeyboardInterrupt` (Ctrl-C)
- **THEN** it stops accepting connections and exits without a traceback

### Requirement: GraphQL HTTP endpoint

The server SHALL expose a GraphQL endpoint at the configured `path` (default `/graphql`). It SHALL accept
`POST` requests with a JSON body containing `query` and optional `variables` and `operationName`, and it
SHALL accept `GET` requests carrying the query in the `query` (and optional `variables`/`operationName`)
URL parameters. For each request it SHALL `await execute(schema, ...)` and return the result as an
`application/json` body of the form `{data, errors}`.

#### Scenario: POST a query

- **WHEN** a client sends `POST /graphql` with body `{"query": "{ __typename }"}`
- **THEN** the response is `200` with an `application/json` body whose `data` contains the result

#### Scenario: Query via GET

- **WHEN** a client sends `GET /graphql?query={__typename}`
- **THEN** the response is `200` with the executed result as JSON

#### Scenario: Variables forwarded

- **WHEN** a `POST /graphql` body includes `variables` and `operationName`
- **THEN** those values are passed to `execute` and influence the result

### Requirement: HTTP error responses

The server SHALL return appropriate HTTP status codes for malformed or unsupported requests: a request
body that is not valid JSON SHALL yield `400`, a request to an unknown path SHALL yield `404`, and an
unsupported method on a known path SHALL yield `405`. GraphQL-level errors (parse/validation/resolver)
SHALL still return `200` with the errors in the `errors` array, per GraphQL-over-HTTP convention.

#### Scenario: Malformed JSON body

- **WHEN** a client sends `POST /graphql` with a body that is not valid JSON
- **THEN** the response status is `400`

#### Scenario: Unknown path

- **WHEN** a client requests a path the server does not serve
- **THEN** the response status is `404`

#### Scenario: GraphQL error stays 200

- **WHEN** a syntactically valid request contains a query that fails validation
- **THEN** the response status is `200` and the body's `errors` array describes the failure
