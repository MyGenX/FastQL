# tracing-instrumentation Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: OpenTelemetry tracing extension

FastQL SHALL provide an optional OpenTelemetry schema extension (behind an extra)
that emits spans for the operation and for each resolved field, recording the
operation name, field path, and errors. It MUST NOT be imported by the core.

#### Scenario: Spans emitted per operation and field

- **WHEN** the OpenTelemetry extension is enabled and an operation executes
- **THEN** a parent span is created for the operation and child spans for resolved fields, with errors recorded on the relevant span

#### Scenario: No-op without dependency

- **WHEN** the OpenTelemetry package is not installed
- **THEN** importing the core and running operations works unchanged and the extension is simply unavailable

### Requirement: Apollo-style tracing extension

FastQL SHALL provide a tracing extension that records per-field timing and merges
an Apollo-style `tracing` block into `ExecutionResult.extensions`.

#### Scenario: Tracing block present in extensions

- **WHEN** the tracing extension is enabled and an operation executes
- **THEN** the result's `extensions` contains start/end timestamps, total duration, and per-field resolver durations

