## MODIFIED Requirements

### Requirement: Dependency-free base installation

The base FastQL distribution SHALL retain no mandatory third-party runtime dependencies. Installing FastQL alone SHALL provide the custom GraphQL engine, development server, shared integration contract, and generic ASGI adapter. The GraphQL-core operation backend SHALL remain optional and SHALL NOT be imported by base FastQL modules or default FastQL operation execution.

#### Scenario: Base wheel metadata

- **WHEN** the FastQL wheel is built without selecting an extra
- **THEN** its mandatory dependencies do not include GraphQL-core, FastAPI, Starlette, Flask, Django, or a production ASGI server

#### Scenario: Core import in a clean environment

- **WHEN** only the base distribution is installed
- **THEN** importing and using the default FastQL parser, validator, executor, subscriptions, integrations package, and test client succeeds without GraphQL-core or a supported framework installed

## ADDED Requirements

### Requirement: Optional GraphQL-core backend extra

The distribution SHALL define an independently installable `graphql-core` extra requiring the stable `graphql-core~=3.2.0` line and excluding 3.3 prereleases. Selecting the GraphQL-core backend or importing its integration without the dependency SHALL fail with an actionable message naming `fastql[graphql-core]`. The aggregate `all` extra SHALL include the GraphQL-core backend dependency.

#### Scenario: GraphQL-core extra selected

- **WHEN** a user installs `fastql[graphql-core]`
- **THEN** GraphQL-core 3.2 and the FastQL integration can be imported without installing a web framework

#### Scenario: Optional dependency missing

- **WHEN** GraphQL-core is absent and a user selects `operation_backend="graphql-core"`
- **THEN** schema construction tells the user to install `fastql[graphql-core]`

#### Scenario: Aggregate extra selected

- **WHEN** a user installs `fastql[all]`
- **THEN** every first-party framework adapter and the optional GraphQL-core backend can be imported

#### Scenario: Prerelease backend excluded

- **WHEN** package metadata is inspected
- **THEN** the GraphQL-core requirement accepts compatible stable 3.2 releases and does not opt into 3.3 prereleases
