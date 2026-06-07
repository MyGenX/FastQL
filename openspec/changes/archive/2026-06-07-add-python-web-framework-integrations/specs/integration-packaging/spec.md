## ADDED Requirements

### Requirement: Dependency-free base installation

The base `fastql` distribution SHALL retain no mandatory web-framework runtime dependencies. Installing `fastql` alone SHALL provide the core GraphQL engine, development server, shared integration contract, and generic ASGI adapter.

#### Scenario: Base wheel metadata

- **WHEN** the FastQL wheel is built without selecting an extra
- **THEN** its mandatory dependencies do not include FastAPI, Starlette, Flask, Django, or a production ASGI server

#### Scenario: Core import in a clean environment

- **WHEN** only the base distribution is installed
- **THEN** importing and using core FastQL functionality succeeds without any supported framework installed

### Requirement: Independent framework extras

The distribution SHALL define independently installable extras named `asgi`, `starlette`, `fastapi`, `flask`, and `django`. Selecting one framework extra SHALL install only dependencies required by that integration and their normal transitive dependencies.

#### Scenario: FastAPI extra selected

- **WHEN** a user installs `fastql[fastapi]`
- **THEN** the FastAPI integration dependencies are installed without adding Flask or Django

#### Scenario: Django extra selected

- **WHEN** a user installs `fastql[django]`
- **THEN** the Django integration dependencies are installed without adding FastAPI or Flask

### Requirement: Aggregate integration extra

The distribution SHALL provide an `all` extra that includes the dependency requirements of every first-party framework integration.

#### Scenario: All integrations selected

- **WHEN** a user installs `fastql[all]`
- **THEN** every first-party framework adapter can be imported

### Requirement: Optional import isolation

Importing `fastql` or the framework-neutral `fastql.integrations` package SHALL NOT import an optional framework. Importing an adapter whose dependency is absent SHALL fail with an actionable message naming the corresponding installation extra.

#### Scenario: Missing Flask dependency

- **WHEN** Flask is not installed and a user imports the Flask adapter
- **THEN** the import error tells the user to install `fastql[flask]`

#### Scenario: Unrelated adapter remains usable

- **WHEN** only the Django extra is installed
- **THEN** core FastQL and the Django adapter work without importing FastAPI, Starlette, or Flask

### Requirement: Declared compatibility and packaging validation

FastQL SHALL document supported framework version ranges and SHALL validate wheel metadata, isolated imports, and a representative supported-version matrix in automated tests.

#### Scenario: Package metadata matches documentation

- **WHEN** release validation inspects optional dependencies and the compatibility documentation
- **THEN** every first-party adapter has a matching extra and supported version declaration

