# Design — Docs Categorization Audit

## Context

The docs navigation (`docs/docs.json`) currently has 10 groups; "Advanced capabilities" holds 12 pages spanning data loading, protocol features, federation, observability, testing, and a Pydantic integration. An audit against Strawberry's topic tree (the ecosystem reference for code-first Python GraphQL) confirmed the grouping is overloaded and identified missing topics. The site is Mintlify-based; page URLs mirror file paths, and `docs.json` supports a `redirects` array.

Audit outcome — coverage map (Strawberry topic → FastQL page):

| Strawberry topic | FastQL coverage |
| --- | --- |
| General / Schema basics / Queries / Mutations | `start/*`, `build/operations-and-schema` |
| Subscriptions + Multipart subscriptions | `advanced/subscriptions` |
| Errors / Dealing with errors / Exceptions | `resolve/errors-and-nullability` |
| Object / Input / Interface / Enum / Union types | `build/types-and-fields`, `build/inputs-and-abstract-types` |
| Scalars | `reference/scalars-and-wrappers`, `build/inputs-and-abstract-types` |
| Schema configurations | `build/naming-and-configuration` |
| Schema directives / Private fields | `advanced/directives-and-visibility` |
| Generics | `advanced/generic-types` |
| Resolvers / Accessing parent data | `resolve/resolvers`, `resolve/context-and-info` |
| Defer and Stream | `advanced/incremental-delivery` |
| DataLoaders | `advanced/dataloader` |
| Schema extensions / Field extensions | `advanced/schema-extensions`, `resolve/extensions-and-permissions` |
| Relay / Pagination | `advanced/relay-pagination` |
| File upload / Query batching | `advanced/uploads-and-batching` |
| Permissions | `resolve/extensions-and-permissions` |
| Built-in server / Tools / Schema export | `tooling/dev-server`, `tooling/cli`, `tooling/schema-output` |
| Federation | `advanced/federation` (single page; Strawberry has a 4-page section) |
| Integrations (per framework) | `integrations/*` |
| Pydantic | `advanced/pydantic` |
| Testing / Tracing | `advanced/testing-and-export`, `advanced/observability` |
| **FAQ** | missing → new page |
| **Authentication** | missing (scattered mentions) → new page |
| **Deployment** | missing (touched in `integrations/overview`) → new page |
| **Lazy types** | missing; engine supports forward refs (`fastql/decorators/annotations.py`) → new page |
| **Codegen (schema/query)** | no feature → roadmap only |
| **Editor integration / Mypy** | missing → roadmap only |
| **Upgrading / Breaking changes** | premature pre-1.0 → roadmap only |
| **Convert to dictionary** | Strawberry-specific → not applicable |

## Goals / Non-Goals

**Goals**
- Navigation where every group has one theme and no group exceeds ~6 pages.
- URLs that match the new grouping, with old URLs redirecting.
- Pages for every topic whose underlying feature already exists.
- A public roadmap of deferred documentation topics.

**Non-Goals**
- New engine features (codegen, persisted operations).
- Content rewrites beyond the federation split and link fixes in moved pages.
- Versioning/upgrade documentation.

## Decisions

1. **Move files to directories matching the new groups, with redirects** (over keeping files in `advanced/` under new nav groups). Mintlify URLs mirror paths, so leaving 12 pages under `/advanced/...` while the sidebar says "Protocol features" would be permanently incongruent; a one-time move plus `redirects` entries in `docs.json` is cheap and final. Alternative (in-place regroup) rejected: avoids churn now but bakes in misleading URLs.

2. **Target layout** (group → pages; `*` = new file, `→` = moved from `advanced/`):
   - **Start**: existing + `start/faq`\*
   - **Build schemas**: existing 4 + `build/generic-types`→ + `build/directives-and-visibility`→ + `build/lazy-types`\*
   - **Resolve data**: existing 5 + `resolve/authentication`\*
   - **Data & performance**: `data/dataloader`→, `data/schema-extensions`→, `data/relay-pagination`→
   - **Protocol features**: `protocol/subscriptions`→, `protocol/incremental-delivery`→, `protocol/uploads-and-batching`→
   - **Federation**: `federation/overview`\*, `federation/entities`\*, `federation/custom-directives`\* (content split from `advanced/federation.mdx`)
   - **Integrations**: existing 6 + `integrations/pydantic`→
   - **Operations**: `operations/deployment`\*, `operations/testing-and-export`→, `operations/observability`→
   - **Tooling / Reference / Architecture / Specifications / Contribute**: unchanged
   - `docs/advanced/` directory is removed at the end.

3. **Federation split** carves the existing page by its natural seams — setup/overview, entity resolution (`@key`, reference resolvers), and custom federation directives — rather than writing new material; gaps found during the split (e.g., entity interfaces) go to the roadmap, not into scope.

4. **Roadmap lives in `start/project-status.mdx`** as a `## Planned` section (codegen, editor/mypy guidance, upgrading & breaking changes, dedicated field-extensions page, federation entity interfaces). The page already lists "Implemented" and "Current boundaries", so readers already use it as the status source. Alternative (separate roadmap page) rejected as a third status location to keep in sync.

5. **Internal links are updated to the new paths** (grep for `/advanced/` across `docs/**/*.mdx`, notably `index.mdx`, `start/project-status.mdx`, `specifications/capability-catalog.mdx`); redirects exist only for external/bookmarked links, not as an excuse for stale internal ones.

## Risks / Trade-offs

- [Moved URLs break external links] → `redirects` array in `docs.json` maps every old `/advanced/...` path to its new location; broken-link check validates internal ones.
- [Federation split produces thin pages] → acceptable; the section is expected to grow (entity interfaces on roadmap), and thin-but-findable beats one long page.
- [New guides (auth, deployment) describe patterns, not built-ins — FastQL core has no transport/auth] → pages are framed as integration patterns (context + permissions, ASGI deployment) and must respect the core's framework-agnostic boundary.

## Migration Plan

Single PR: regroup `docs.json` + move files + redirects first (site stays green), then federation split, then new pages, then roadmap section and link fixes. Rollback is reverting the PR; no data or code migration.

## Open Questions

None — nav strategy (hybrid regroup) and roadmap placement (public, in project-status) were decided with the user during planning.
