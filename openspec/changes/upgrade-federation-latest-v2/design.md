## Context

Federation is currently layered through `fastql.federation.Schema`, which builds a normal FastQL schema and then adds Federation v2.7 directive definitions, `_service`, and `_entities`. This ordering means decorated definitions are validated before federation definitions exist. The shared SDL endpoint and CLI call the core printer directly, so they render executable support types instead of the gateway-facing subgraph SDL. Reference resolvers also remain in a process-global registry after schema construction.

The latest Federation feature definition supported by Apollo's federation repository on June 12, 2026 is v2.14. FastQL must remain dependency-free and cannot fetch specification metadata at runtime, so support must be represented locally and updated intentionally with FastQL releases.

## Goals / Non-Goals

**Goals:**

- Keep `fastql.federation.Schema` as the canonical, explicit federation entry point.
- Provide a version-aware Federation v2 contract with v2.14 as the default and latest supported version.
- Validate federation metadata while building the schema rather than after construction.
- Give every SDL consumer one schema-aware rendering path.
- Make entity definitions, resolvers, and representation validation deterministic and schema-local.
- Cover the supported contract with unit, integration, and optional composition tests.

**Non-Goals:**

- Federation v1, gateway/router behavior, or supergraph composition in the FastQL runtime.
- Runtime downloads or automatic discovery of new Federation versions.
- Runtime enforcement of composition metadata such as authentication, policy, cost, context, or cache directives; FastQL validates and publishes this metadata for routers.
- Framework-specific federation branches or new runtime dependencies.

## Decisions

### Keep a versioned federation subclass

`fastql.federation.Schema` remains canonical and accepts `federation_version`, defaulting to `LATEST_FEDERATION_VERSION == "2.14"`. A local capability table describes supported versions, directive availability, argument shapes, repeatability, feature types, and link imports. Unsupported versions fail construction with a clear error.

This is preferred over adding federation configuration to core `Schema`, because federation remains an explicit opt-in layer and the user selected the subclass API. A floating network-backed "latest" value is rejected because it would make schema output nondeterministic and violate the dependency-free runtime constraint.

### Inject directive definitions before core validation

The core schema build path will accept additional directive definitions and merge them with built-ins and registry-defined directives before `_validate_applied_directives` runs. The federation subclass computes definitions for the selected version and supplies them during `super().__init__`, rather than installing definitions afterward.

Directive validation will also enforce required arguments and non-repeatable usage. Existing unknown custom directives continue to follow the current custom-directive policy, while names owned by the selected Federation version are always validated. This narrow builder extension is preferred over duplicating the entire schema builder in `fastql.federation`.

### Add explicit schema-level federation metadata

The subclass accepts `schema_directives: list[AppliedDirective] | None` for directives whose location is `SCHEMA`, including `@composeDirective` and `@tag`. The existing `directives` mapping remains directive-definition input and is not overloaded. The generated federation `@link` remains automatic and is not authored manually.

Applied directives will be supported consistently on every location advertised by their definitions. This includes adding directive metadata and SDL rendering for enum values and preserving argument/input-field directive rendering already represented by the IR.

### Publish SDL through a schema-owned rendering hook

Core `print_schema(schema)` will dispatch through a schema rendering hook when one is present; otherwise it retains current behavior. The federation subclass hook returns gateway-facing subgraph SDL with the selected version's `@link` declaration and omits `_service`, `_entities`, `_Any`, `_Entity`, `_Service`, and other generated support definitions.

The low-level core renderer remains separately callable inside federation rendering to prevent recursion. `_service`, the shared HTTP handler, framework adapters, and CLI export all continue calling the public `print_schema`, producing identical output without transport-specific type checks.

### Parse and validate federation field sets

`@key`, `@requires`, and `@provides` values will be parsed as GraphQL field selections by wrapping them in a synthetic operation and using FastQL's language parser. Validation resolves selections against the annotated type, rejects arguments/directives/aliases where Federation field sets prohibit them, validates nested selections, and records normalized key metadata on the federated schema.

This is preferred over string splitting because compound and nested field sets are valid Federation syntax. Full supergraph composition rules remain Rover's responsibility; FastQL performs the local structural checks required to produce a coherent subgraph.

### Snapshot entity resolvers and metadata per schema

The decorator registry remains a convenient collection mechanism, but the federation schema snapshots applicable reference resolvers during construction. Runtime `_entities` resolution reads only this immutable schema-owned mapping. Registration is associated with decorated Python types and converted to GraphQL names during construction, preventing collisions between independent schemas that use the same GraphQL name.

An object enters `_Entity` only when it has at least one `@key` with `resolvable: true`. Every such entity must have a captured resolver; otherwise schema construction fails. Types with only non-resolvable keys remain in published SDL but do not enter `_Entity`.

### Validate representations before invoking user code

Each representation must be an object with a string `__typename`, target a member of `_Entity`, and satisfy all fields of at least one declared resolvable key. Invalid entries produce GraphQL errors whose paths identify the representation index. A resolver returning `None` remains the valid not-found result. Sync and async resolvers retain ordered execution semantics and may receive the full representation, individual key fields, and `Info` through the existing signature adapter.

### Treat v2.14 directives as metadata capabilities

The capability table includes the existing directives plus `@extends`, `@composeDirective`, `@interfaceObject`, `@authenticated`, `@requiresScopes`, `@policy`, `@context`, `@fromContext`, `@cost`, `@listSize`, and `@cacheTag`, with their version gates through v2.14. Helpers return ordinary `AppliedDirective` values and do not implement router behavior.

## Risks / Trade-offs

- [Latest Federation behavior can change after release] -> Pin v2.14 in code and update the constant, capability table, fixtures, and changelog together in future releases.
- [Stricter validation can reject schemas previously accepted] -> Raise actionable build errors naming the directive, location, field set, or missing resolver; document this as correctness hardening.
- [Core SDL dispatch could recurse or affect normal schemas] -> Separate raw rendering from public dispatch and retain regression tests for non-federated schemas.
- [Local validation cannot reproduce all composition rules] -> Validate schema-local invariants and use optional Rover fixtures for cross-subgraph composition conformance.
- [Global decorator registration still exists before build] -> Snapshot by Python type during schema construction and clear only through the existing test utility; runtime never consults mutable global state.

## Migration Plan

1. Add the version model, directive definitions/helpers, and pre-build directive injection while preserving existing v2.7 authoring calls.
2. Add schema-owned SDL dispatch and update all schema publication paths through the existing public printer.
3. Add field-set/entity metadata validation and schema-local resolver snapshots.
4. Add latest-v2 directive coverage, documentation, and optional Rover composition fixtures.
5. Release with v2.14 as the default. Users needing stable older output can pass a supported explicit `federation_version`.

Rollback is isolated: the default can be returned to v2.7 while retaining the version table, and schema-aware rendering can be disabled by removing the federation hook without changing framework adapters.

## Open Questions

None. Federation v2.14, the subclass API, release-pinned latest behavior, and metadata-only semantics for router directives are fixed for this change.
