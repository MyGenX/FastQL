## ADDED Requirements

### Requirement: Serve an in-browser GraphQL IDE

The server SHALL serve a GraphiQL in-browser IDE as an HTML page at `GET /`. The page SHALL load GraphiQL
assets from a CDN and SHALL be configured to send operations to the server's configured GraphQL endpoint
path. The IDE SHALL allow the user to run queries and SHALL expose a documentation/schema explorer driven
by introspection so the user can browse the schema.

#### Scenario: Playground page served

- **WHEN** a browser requests `GET /`
- **THEN** the response is `200` with `text/html` containing the GraphiQL bootstrap and a reference to the GraphQL endpoint path

#### Scenario: Endpoint path reflected

- **WHEN** the server is started with a non-default `path` (e.g. `/api/graphql`)
- **THEN** the served GraphiQL page is configured to send operations to that same path

#### Scenario: Schema explorer works

- **WHEN** the user opens GraphiQL and the server's schema is reachable
- **THEN** GraphiQL's docs explorer lists the schema's types and fields via introspection
