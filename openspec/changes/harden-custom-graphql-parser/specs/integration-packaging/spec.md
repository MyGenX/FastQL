## MODIFIED Requirements

### Requirement: Dependency-free base installation

The base FastQL distribution SHALL retain no mandatory third-party runtime dependencies. Installing FastQL alone SHALL provide the custom GraphQL lexer, parser, AST, validator, executor, development server, shared integration contract, and generic ASGI adapter. GraphQL-core, GraphQL.js corpus tooling, property/fuzz libraries, and benchmark tooling SHALL remain development-only and SHALL NOT appear in runtime wheel metadata or be imported by normal FastQL operation.

#### Scenario: Base wheel metadata

- **WHEN** the FastQL wheel is built without selecting an extra
- **THEN** its mandatory dependencies do not include GraphQL-core, parser generators, fuzzing/benchmark packages, FastAPI, Starlette, Flask, Django, or a production ASGI server

#### Scenario: Core import in a clean environment

- **WHEN** only the base distribution is installed
- **THEN** importing, parsing, validating, and executing with core FastQL succeeds without GraphQL-core, test tooling, or any supported framework installed

#### Scenario: Development oracle isolation

- **WHEN** conformance and differential tests install `graphql-core==3.2.11`
- **THEN** the oracle is used only by tests and benchmark tooling and is not imported by the `fastql` runtime package

#### Scenario: Generated conformance fixtures run offline

- **WHEN** routine tests run without network access or a Node.js installation
- **THEN** committed GraphQL.js-derived fixtures execute successfully from their recorded provenance and checksums
