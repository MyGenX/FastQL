# server-cli Specification

## Purpose
The `python -m fastql serve module:attr` command-line entry point for launching the dev server.
## Requirements
### Requirement: Launch the server from the command line

The framework SHALL provide a CLI runnable as `python -m fastql serve <target>` where `<target>` is a
dotted import path to a schema object in `module:attr` form (and SHALL also accept `module.attr`). The CLI
SHALL import that object and call `serve(...)` with it. The CLI SHALL accept `--host` and `--port` flags
that override the defaults (`127.0.0.1` and `7691`).

#### Scenario: Serve a schema by dotted path

- **WHEN** a user runs `python -m fastql serve examples.hello:schema`
- **THEN** the CLI imports `schema` from `examples.hello` and starts the dev server on `127.0.0.1:7691`

#### Scenario: Override host and port

- **WHEN** a user runs `python -m fastql serve examples.hello:schema --host 0.0.0.0 --port 9000`
- **THEN** the server binds to `0.0.0.0:9000`

#### Scenario: Invalid target

- **WHEN** the target cannot be imported or does not name a schema object
- **THEN** the CLI exits with a non-zero status and a clear error message naming the target

#### Scenario: Graceful interrupt

- **WHEN** the user presses Ctrl-C while the CLI server is running
- **THEN** the CLI exits cleanly with a shutdown message and no traceback

