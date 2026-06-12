# Tasks — Docs Categorization Audit

## 1. Regroup navigation and move pages

- [x] 1.1 Move pages out of `docs/advanced/` per the design layout: `generic-types` and `directives-and-visibility` to `docs/build/`, `pydantic` to `docs/integrations/`, `dataloader`/`schema-extensions`/`relay-pagination` to `docs/data/`, `subscriptions`/`incremental-delivery`/`uploads-and-batching` to `docs/protocol/`, `testing-and-export`/`observability` to `docs/operations/`
- [x] 1.2 Rewrite `docs/docs.json` navigation groups: Start, Build schemas, Resolve data, Data & performance, Protocol features, Federation, Integrations, Operations, Tooling, Reference, Architecture, Specifications, Contribute
- [x] 1.3 Add a `redirects` array to `docs/docs.json` mapping every old `/advanced/...` URL to its new path
- [x] 1.4 Update internal links pointing at `/advanced/...` across `docs/**/*.mdx` (notably `index.mdx`, `start/project-status.mdx`, `specifications/capability-catalog.mdx`)

## 2. Split federation into a section

- [x] 2.1 Split `docs/advanced/federation.mdx` into `docs/federation/overview.mdx` (setup and concepts), `docs/federation/entities.mdx` (`@key`, reference resolvers), and `docs/federation/custom-directives.mdx`; add cross-links between the three pages
- [x] 2.2 Add the federation pages to the Federation nav group and a redirect from `/advanced/federation`; delete the now-empty `docs/advanced/` directory

## 3. Write new pages

- [x] 3.1 Write `docs/start/faq.mdx` covering common evaluation questions (Strawberry comparison, zero dependencies, async-first execution, transport boundary, maturity)
- [x] 3.2 Write `docs/build/lazy-types.mdx` documenting string/forward-reference annotations and circular type references, verified against `fastql/decorators/annotations.py` behavior with a runnable example
- [x] 3.3 Write `docs/resolve/authentication.mdx` presenting authentication as an integration pattern: credentials extracted in the transport layer, passed via context, enforced with permissions/field extensions
- [x] 3.4 Write `docs/operations/deployment.mdx` covering production deployment through framework adapters (ASGI workers, subscriptions transport, dev-server warnings), respecting the no-transport core boundary

## 4. Roadmap and validation

- [x] 4.1 Add a `## Planned` section to `docs/start/project-status.mdx` listing deferred documentation topics: schema/query codegen, editor integration / mypy guidance, upgrading & breaking-changes pages, dedicated field-extensions page, federation entity interfaces
- [x] 4.2 Run the documented docs quality checks from `docs/` (Mintlify build/strict validation and broken-link check including anchors) and fix any failures
- [x] 4.3 Verify every `docs.json` navigation entry resolves to an existing MDX file and no orphaned `.mdx` files remain outside the navigation
