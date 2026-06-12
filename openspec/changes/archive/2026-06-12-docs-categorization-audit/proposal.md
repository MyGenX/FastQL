# Docs Categorization Audit

## Why

An audit of the FastQL docs against the topic tree of the leading code-first Python GraphQL framework (Strawberry) shows two problems: the "Advanced capabilities" group has grown to 12 unrelated pages (data loading, protocol features, federation, observability, testing all mixed together), and several ecosystem-standard topics readers will look for — FAQ, authentication, deployment, lazy/forward-reference types, federation deep dives — have no page at all. Fixing the grouping now keeps the navigation scalable as new capability docs land, and recording the missing topics gives the docs backlog a visible home.

## What Changes

- Regroup `docs/docs.json` navigation: dissolve "Advanced capabilities" into themed groups — **Data & performance** (dataloader, schema-extensions, relay-pagination), **Protocol features** (subscriptions, incremental-delivery, uploads-and-batching), **Federation** (own section), and **Operations** (deployment, testing-and-export, observability).
- Move misplaced pages to task-appropriate groups: `generic-types` and `directives-and-visibility` into **Build schemas**; `pydantic` into **Integrations**.
- Split the single `advanced/federation.mdx` into a Federation section: introduction, entities, and custom federation directives.
- Add new pages for covered-but-undocumented topics: **FAQ** (Start), **Authentication guide** (Resolve data), **Deployment guide** (Operations), and **Lazy / forward-reference types** (Build schemas — engine support confirmed in `fastql/decorators/annotations.py`).
- Add a public **"Planned" roadmap section** to `start/project-status.mdx` listing topics deferred until their features exist: schema/query codegen, editor integration / mypy guidance, upgrading & breaking-changes pages, dedicated field-extensions page.
- Add Mintlify redirects for any moved page paths so existing links keep resolving.

## Capabilities

### New Capabilities

None — this change reorganizes and extends documentation; no engine or tooling capability is introduced.

### Modified Capabilities

- `documentation-site`: the "Task-oriented documentation navigation" requirement changes — the navigation taxonomy gains data & performance, protocol features, federation, and operations areas (replacing the catch-all advanced area), and new requirements cover ecosystem-standard topic coverage (FAQ, authentication, deployment, lazy types) and a public roadmap of planned documentation topics.

## Impact

- `docs/docs.json` — navigation groups restructured; redirects added.
- `docs/advanced/*.mdx` — pages redistributed into new directories/groups (with redirects); `federation.mdx` split into three pages.
- New MDX pages: FAQ, authentication, deployment, lazy types; `docs/start/project-status.mdx` gains a roadmap section.
- No Python code, public API, or runtime dependency changes; the core stays web-framework-agnostic.

## Non-goals / Out of scope

- Implementing codegen, persisted operations, or any engine feature — only their documentation backlog entries.
- Upgrading/breaking-changes pages (deferred until a versioning policy exists post-1.0).
- A "convert to dictionary" utility page (Strawberry-specific; not applicable to FastQL).
- Rewriting existing page content beyond what the federation split and moves require.
