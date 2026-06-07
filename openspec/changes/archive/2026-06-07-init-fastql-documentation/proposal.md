## Why

FastQL currently explains the framework through a single README, which is insufficient for introducing the product vision, teaching the unified authoring API, and maintaining detailed technical specifications as the project grows. A dedicated documentation site will give users a clear path from first impression to working schema while giving contributors a durable reference for architecture and behavior.

## What Changes

- Add a Mintlify documentation project under `docs/`, versioned alongside FastQL source code.
- Build a branded custom landing page that explains FastQL's purpose, differentiators, architecture, and primary calls to action without duplicating the documentation sidebar experience.
- Establish navigation for getting started, schema authoring, execution and context, developer tooling, API reference, architecture, project specifications, and contribution guidance.
- Convert the current README quickstart and verified framework behavior into focused MDX pages with runnable examples and cross-links.
- Add product documentation covering the project idea, intended audience, design principles, current maturity, scope, and non-goals.
- Add technical documentation covering public APIs, the parser-to-executor pipeline, schema IR, validation, dependency injection, extensions, introspection, dev server, and CLI.
- Publish human-readable specification pages derived from the maintained OpenSpec capabilities, with links back to their source files rather than duplicating them as an independent source of truth.
- Add local preview and validation instructions using Mintlify's current `docs.json`, MDX, and `mint dev` workflow.

### Non-goals / Out of Scope

- No changes to FastQL runtime behavior, transport architecture, or public Python APIs.
- No Mintlify account provisioning, custom domain, GitHub App installation, or live deployment requiring external credentials.
- No automated Python API extraction or generated OpenAPI reference in the initial documentation foundation.
- No separate documentation repository, multilingual site, blog, changelog system, or versioned release documentation in this change.

## Capabilities

### New Capabilities

- `documentation-site`: A repository-local Mintlify site with a product landing page, task-oriented framework documentation, technical reference, architecture/specification content, and local quality validation.

### Modified Capabilities

None.

## Impact

This change adds a `docs/` project, documentation assets, Mintlify configuration, and contributor validation commands. It updates the repository README to direct readers to the documentation project while keeping the README useful as a concise package overview. The Python package remains zero-runtime-dependency; any Node.js/Mintlify tooling is documentation-development-only and isolated from package metadata.
