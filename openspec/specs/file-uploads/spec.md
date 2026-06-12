# file-uploads Specification

## Purpose
TBD - created by archiving change production-grade-platform. Update Purpose after archive.
## Requirements
### Requirement: Upload scalar

FastQL SHALL provide an `Upload` scalar usable as an input type that represents an
uploaded file (filename, content type, and a readable stream) at resolution time.

#### Scenario: Upload argument typed

- **WHEN** a mutation declares an argument of type `Upload`
- **THEN** the schema exposes that argument as the `Upload` scalar and the resolver receives a file-like object

### Requirement: Multipart request parsing

The HTTP integration layer SHALL parse `multipart/form-data` requests per the
graphql-multipart-request-spec: an `operations` field, a `map` field, and file
parts, substituting files into the operation variables by the map paths.

#### Scenario: Single file mapped into variables

- **WHEN** a multipart request maps one file part to `variables.file`
- **THEN** the resolver receives that file as the value of the `file` variable

#### Scenario: Multiple files mapped

- **WHEN** a multipart request maps several file parts to a list variable
- **THEN** each file is substituted at its mapped path in the operation variables

#### Scenario: Malformed map rejected

- **WHEN** the `map` references a path that does not exist in `operations`
- **THEN** the request is rejected with a client error

