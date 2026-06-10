## ADDED Requirements

### Requirement: Export schema as SDL

The FastQL CLI SHALL provide an `export-schema module:attr` command that prints
the schema's SDL to stdout or writes it to a file given an output path.

#### Scenario: SDL written to file

- **WHEN** `fastql export-schema app:schema --output schema.graphql` is run
- **THEN** the file `schema.graphql` contains the schema's SDL

#### Scenario: SDL to stdout by default

- **WHEN** `fastql export-schema app:schema` is run without an output path
- **THEN** the SDL is written to stdout

### Requirement: Export introspection JSON

The export command SHALL support emitting the schema as an introspection result
in JSON format.

#### Scenario: Introspection JSON emitted

- **WHEN** the export command is run with a JSON/introspection format flag
- **THEN** the output is the schema's introspection result as JSON

#### Scenario: Invalid module path reported

- **WHEN** the `module:attr` target cannot be imported or is not a schema
- **THEN** the command exits non-zero with a clear error message
