## MODIFIED Requirements

### Requirement: Export schema as SDL

The FastQL CLI SHALL provide an `export-schema module:attr` command that prints the schema's publishable SDL to stdout or writes it to a file given an output path. Export SHALL use the same schema-aware rendering contract as `print_schema`, including gateway-facing SDL for `fastql.federation.Schema`.

#### Scenario: Standard SDL written to file

- **WHEN** `fastql export-schema app:schema --output schema.graphql` is run for a non-federated schema
- **THEN** the file `schema.graphql` contains the schema's standard SDL

#### Scenario: Federated SDL written to file

- **WHEN** the export command targets a federated schema
- **THEN** the output contains the selected-version federation `@link`, matches `_service.sdl`, and excludes generated federation execution fields and support types

#### Scenario: SDL to stdout by default

- **WHEN** `fastql export-schema app:schema` is run without an output path
- **THEN** the schema-aware SDL is written to stdout
