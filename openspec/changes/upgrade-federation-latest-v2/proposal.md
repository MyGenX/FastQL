## Why

FastQL advertises Apollo Federation v2 support, but the implementation is pinned to v2.7 and is not consistently integrated with schema building, HTTP schema endpoints, or CLI export. Invalid federation metadata can pass schema construction, published SDL can omit `@link` while exposing runtime support types, and process-global reference resolvers can leak across schemas.

## What Changes

- Keep `fastql.federation.Schema` as the canonical opt-in API and add an explicit, version-aware Federation configuration pinned by default to the latest FastQL-supported Federation release.
- Upgrade the supported contract to Federation v2.14, including version-gated directive definitions, feature links, helper APIs, and supporting scalar types introduced through v2.14.
- Validate federation directives and field sets during schema construction, including directive locations, arguments, repeatability, selected Federation version, and referenced fields.
- Make `print_schema`, `_service`, HTTP schema endpoints, framework adapters, and CLI SDL export publish the same gateway-facing subgraph SDL.
- Store entity metadata and reference resolver bindings on each federated schema, validate incoming representations against declared resolvable keys, and isolate schemas from process-global resolver mutations.
- Add composition-level conformance coverage for representative latest-v2 schemas while keeping Rover optional and development-only.

### Non-goals / Out of Scope

- Federation v1 compatibility, gateway/router implementation, schema composition inside FastQL, and runtime fetching of specification metadata are out of scope.
- This change does not add transport-specific federation behavior; existing framework adapters continue to consume the shared HTTP handler.
- The dependency-free core remains unchanged as a packaging constraint; external composition tooling is test-only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `apollo-federation`: Upgrade the subgraph contract to version-aware Federation v2.14 support, validated directives and field sets, schema-owned entity resolution, and stricter representation handling.
- `schema-endpoints`: Require federated schemas to publish gateway-facing subgraph SDL consistently through shared HTTP and framework endpoints.
- `schema-export-cli`: Require SDL export to preserve the selected schema's federation-aware rendering contract.

## Impact

- Federation modules, schema construction and validation, SDL rendering, the shared HTTP integration, and CLI schema export will change.
- Public additions include a latest-version constant, a selected-version option on `fastql.federation.Schema`, and helpers for Federation directives introduced after v2.7.
- Existing `fastql.federation.Schema`, directive helpers, `reference_resolver`, `print_federated_schema`, and `Field(external=True)` remain supported.
- Tests expand across federation execution, schema building, HTTP/framework integrations, CLI export, and optional Rover composition fixtures. No runtime dependency is added.
