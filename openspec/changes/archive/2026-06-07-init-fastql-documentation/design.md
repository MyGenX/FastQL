## Context

FastQL has a concise README, executable examples, tests, and detailed OpenSpec capability specifications, but no documentation information architecture or hosted-docs source. The documentation must serve two audiences: Python developers evaluating or adopting FastQL, and contributors reasoning about its hand-built GraphQL engine. It must remain accurate while the framework is pre-1.0 and evolving quickly.

Mintlify is selected because its current docs-as-code model uses repository MDX pages, a required `docs.json` configuration, custom page modes for landing pages, and local validation commands. It can build from a repository subdirectory, so documentation can remain coupled to the code version without adding runtime dependencies to the Python package.

## Goals / Non-Goals

**Goals:**
- Create a polished first documentation release that explains the product before exposing implementation detail.
- Give new users a verified path from installation to defining, serving, and executing a schema.
- Document the public authoring, execution, context, extension, and tooling APIs represented by current code and tests.
- Expose architecture and capability specifications without creating a second specification source of truth.
- Make documentation locally previewable, link-checked, accessible, and build-validatable.

**Non-Goals:**
- No runtime code or public API changes.
- No live Mintlify provisioning, credentials, custom domain, analytics, search tuning, or deployment automation requiring account access.
- No generated Python API reference, release versioning, translations, blog, or changelog.

## Decisions

### Repository-local Mintlify project

The documentation source lives in `docs/`. `docs/docs.json` uses Mintlify's current schema reference, the `mint` theme, Lucide icons, system light/dark appearance, FastQL branding, and grouped navigation. `docs/package.json` contains only documentation tooling with a locked `mint` development dependency and scripts for preview, strict validation, broken links, accessibility, and the combined check. Node.js 20.17+ is documented as a docs-only prerequisite.

This is preferred over a separate repository because framework behavior, examples, and docs should change in one review. Mintlify deployment can later point at the `docs/` subdirectory through dashboard configuration.

### Information architecture

Navigation is grouped as follows:
- **Start:** introduction, installation, quickstart, first schema, project status.
- **Build schemas:** types and fields, inputs and abstract types, operations and schema assembly, naming and configuration.
- **Resolve data:** resolvers, context and typed info, dependencies, extensions and permissions, errors and nullability.
- **Tooling:** dev server and playground, CLI, SDL and introspection endpoints.
- **Reference:** public API overview, decorators and metadata, schema/execution API, scalar and wrapper types.
- **Architecture:** system overview, language pipeline, type system and schema compilation, validation and execution.
- **Specifications:** product principles and scope, capability catalog, and links to canonical OpenSpec sources.
- **Contribute:** development setup, documentation workflow, and contribution expectations.

Every page has a single user intent, concise frontmatter, related-topic links, and code examples copied from or tested against the current public API.

### Product landing page

`docs/index.mdx` uses `mode: custom`. The first viewport presents “FastQL” as the primary signal, a concise offer, installation and quickstart calls to action, and a short runnable schema example without placing the hero inside a card or using a split hero layout. The next section remains visible at common desktop and mobile viewports.

Below the hero, the page explains FastQL through a restrained feature grid, an actual screenshot of the FastQL GraphiQL playground, the parser-to-executor pipeline, and direct routes for evaluators, users, and contributors. Custom styling is scoped through `docs/style.css`; cards use restrained radii and the palette combines green, charcoal, white, and amber accents rather than a one-hue treatment.

Brand assets include light/dark logo variants, a favicon, and an Open Graph image. The playground image must be captured from the current FastQL example schema so the landing page shows the real product rather than generic stock artwork.

### Documentation truth and specifications

Runtime behavior is documented from public exports, tests, `examples/hello.py`, and current OpenSpec requirements. Unsupported or planned features are explicitly labeled and are not presented as available.

OpenSpec remains canonical for normative behavior. Documentation specification pages provide readable summaries and a capability index, linking to the corresponding `openspec/specs/<capability>/spec.md` source on GitHub. They do not copy full normative requirements into independently maintained MDX files.

### Quality gates

Add a small Python docs test that parses `docs.json`, verifies every navigation page exists, checks required frontmatter, rejects duplicate navigation entries, and confirms documented source links target known capability specs. Mintlify validation runs from `docs/` using `mint validate`, `mint broken-links --check-anchors`, and `mint a11y`.

Documentation snippets used for the quickstart and first-schema path are exercised through either imports from `examples/hello.py` or focused pytest examples so they cannot silently diverge from the public API. A docs CI workflow may run these checks without deploying the site.

## Risks / Trade-offs

- [Documentation drifts from pre-1.0 behavior] -> Ground examples in tests and link specifications to canonical OpenSpec sources.
- [Mintlify configuration changes over time] -> Include the official JSON schema, lock the CLI dependency, and use strict validation.
- [Custom landing CSS becomes fragile] -> Scope styles to custom classes and avoid selectors that depend on Mintlify internals.
- [Large initial page count produces shallow content] -> Require each page to answer a defined user task and merge topics that cannot support a useful standalone page.
- [External deployment cannot be verified locally] -> Deliver a fully validated repository source and document the later GitHub App/subdirectory setup separately.

## Migration Plan

Add `docs/` and docs validation without changing package build inputs. Update the root README with a documentation link and a short contributor command section. A future deployment owner can connect the existing repository and select `docs/` as the documentation subdirectory; no content migration will be required.

## Open Questions

None. The implementation uses the repository-local, complete-foundation, repository-ready defaults described above.
