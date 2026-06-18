## 1. Versioned Federation Build Contract

- [ ] 1.1 Add `LATEST_FEDERATION_VERSION`, supported-version parsing, and a capability table covering Federation v2.0 through v2.14 directive availability and argument changes.
- [ ] 1.2 Extend the core schema build path to merge caller-supplied directive definitions before applied-directive validation without changing normal `Schema` behavior.
- [ ] 1.3 Strengthen applied-directive validation for required arguments and non-repeatable directives, with clear schema build errors.
- [ ] 1.4 Update `fastql.federation.Schema` to accept `federation_version`, reject unsupported versions, and inject selected-version definitions before building decorated schema types.
- [ ] 1.5 Add pytest coverage for default v2.14 selection, explicit older versions, unsupported versions, directive location/argument errors, repeatability, and non-federated schema regressions.

## 2. Latest v2 Directive Authoring

- [ ] 2.1 Implement versioned definitions and public helpers for `@extends`, `@composeDirective`, `@interfaceObject`, `@authenticated`, `@requiresScopes`, `@policy`, `@context`, `@fromContext`, `@cost`, `@listSize`, and `@cacheTag` while preserving existing helpers.
- [ ] 2.2 Add `schema_directives` support to the federation subclass for validated `SCHEMA` applications without overloading the directive-definition mapping.
- [ ] 2.3 Complete applied-directive storage and SDL rendering for advertised type-system locations, including enum values and schema-level metadata.
- [ ] 2.4 Generate selected-version `@link` imports and required supporting federation scalar definitions deterministically from the capability table.
- [ ] 2.5 Add pytest coverage for every v2.14 helper, schema-level directives, supporting argument shapes, version gates, and rendered imports.

## 3. Schema-Aware SDL Integration

- [ ] 3.1 Split core SDL output into a raw renderer and public schema-aware `print_schema` dispatch hook with unchanged output for normal schemas.
- [ ] 3.2 Implement the federation schema rendering hook so published SDL contains selected-version links and user definitions but excludes generated federation execution fields and support types.
- [ ] 3.3 Route `_service.sdl`, the shared HTTP schema endpoint, all framework adapters, and CLI SDL export through the public schema-aware printer.
- [ ] 3.4 Add pytest coverage proving `print_schema`, `print_federated_schema`, `_service.sdl`, `/schema.graphql`, representative framework adapters, and CLI export produce equivalent federated SDL.
- [ ] 3.5 Add regression tests for standard SDL endpoints, standard CLI export, introspection JSON, and executable federation support-type introspection.

## 4. Field Sets and Entity Metadata

- [ ] 4.1 Add a Federation field-set parser using the FastQL language parser and represent normalized compound and nested selections as schema metadata.
- [ ] 4.2 Validate `@key`, `@requires`, and `@provides` field sets against their applicable object/interface and returned entity types, rejecting malformed or unsupported selection constructs.
- [ ] 4.3 Derive `_Entity` membership from keys with `resolvable: true` and omit `_entities` when no locally resolvable entities exist.
- [ ] 4.4 Add pytest coverage for simple, compound, nested, repeated, alternate, invalid, and `resolvable: false` field-set cases.

## 5. Schema-Local Entity Resolution

- [ ] 5.1 Change reference-resolver registration to retain decorated Python type identity and snapshot applicable resolver bindings onto each federation schema at construction.
- [ ] 5.2 Fail schema construction when an entity with a resolvable key has no captured reference resolver, while allowing entities with only non-resolvable keys.
- [ ] 5.3 Validate each `_entities` representation as an object with a string `__typename` that targets a resolvable entity and satisfies at least one declared resolvable key.
- [ ] 5.4 Report malformed representations as indexed GraphQL errors without invoking user code, while preserving null for valid not-found entities and ordered sync/async resolution.
- [ ] 5.5 Add pytest coverage for same-name entity isolation across schemas, alternate keys, missing key fields, invalid/unknown typenames, resolver signatures, async resolvers, not-found results, and output order.

## 6. Conformance, Documentation, and Release Readiness

- [ ] 6.1 Add representative Federation v2.14 subgraph fixtures and an optional Rover composition test path that skips clearly when Rover is unavailable.
- [ ] 6.2 Update federation, schema output, integration, and CLI documentation with the subclass API, pinned-latest policy, explicit version selection, latest directive helpers, and migration errors.
- [ ] 6.3 Update public exports, API reference material, capability/spec documentation, and changelog entries for the v2.14 default and new helpers.
- [ ] 6.4 Run focused federation/schema endpoint/CLI/framework tests, OpenSpec validation, package build checks, and the complete pytest suite.
