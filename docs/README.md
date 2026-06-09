# FastQL documentation

This directory contains the source for the FastQL documentation site:

**Production URL:** [fastql.vachagan.dev](https://fastql.vachagan.dev)

The site is built and hosted with [Mintlify](https://www.mintlify.com/). Documentation
content lives alongside the FastQL source code so code, tests, specifications, and user
guides can evolve in the same pull request.

## Requirements

- Node.js 20.17 or newer
- npm
- Python 3.11 or newer for executable snippets and repository documentation tests

## Local development

Install the documentation dependencies from this directory:

```bash
cd docs
npm ci
```

Start the local Mintlify preview:

```bash
npm run dev
```

The preview is normally available at `http://localhost:3000`.

Run the documentation checks before publishing changes:

```bash
# From docs/
npm run check

# From the repository root
uv run pytest tests/test_documentation.py
```

The npm check validates `docs.json`, internal links, anchors, and accessibility. The
Python test verifies navigation coverage and executes maintained documentation snippets.

## Project structure

```text
docs/
├── docs.json          # Mintlify theme, navigation, branding, and site metadata
├── index.mdx          # documentation landing page
├── start/             # installation and first-use guides
├── build/             # schema and type authoring
├── resolve/           # resolvers, context, dependencies, and errors
├── integrations/      # ASGI and web-framework adapters
├── tooling/           # development server, CLI, and schema output
├── reference/         # public API reference
├── architecture/      # parser, type system, validation, and execution internals
├── specifications/    # product principles and capability catalog
├── contribute/        # contributor guides
├── snippets/          # executable Python examples used by tests
├── images/            # logos, favicon, social image, and screenshots
└── style.css           # custom landing-page and theme styles
```

Add every published page to the navigation in `docs.json`. Keep user-facing behavior
aligned with the canonical OpenSpec requirements under `../openspec/specs/`.

## Mintlify deployment

The FastQL repository is a monorepo from Mintlify's perspective. Configure the Mintlify
project as follows:

1. Connect `MyGenX/FastQL` through the Mintlify GitHub App.
2. Select the production branch, normally `main`.
3. Enable the monorepo setting in **Git Settings**.
4. Set the documentation path to `/docs` with no trailing slash.
5. Deploy the project and confirm the generated Mintlify URL works before configuring
   the custom domain.

After the GitHub App is connected, pushes to the configured production branch trigger
production deployments. Pull requests may receive Mintlify preview deployments when
that feature is enabled for the project.

## Custom domain

The canonical documentation domain is `fastql.vachagan.dev`.

1. Add `fastql.vachagan.dev` in the Mintlify dashboard's custom-domain settings.
2. Add both verification `TXT` records exactly as shown by Mintlify. Their names are
   based on `_acme-challenge.fastql.vachagan.dev` and
   `_cf-custom-hostname.fastql.vachagan.dev`, but their values are project-specific.
3. Wait until both records show as verified and TLS provisioning is ready.
4. Add the following DNS record for the `vachagan.dev` zone:

   ```text
   Type:   CNAME
   Name:   fastql
   Target: cname.mintlify.builders
   ```

5. Wait for DNS propagation and verify that
   `https://fastql.vachagan.dev` serves a valid certificate and the latest deployment.

Do not point the CNAME at Mintlify before its verification records pass; doing so can
delay or interrupt HTTPS provisioning. If the zone has restrictive CAA records, allow
Let's Encrypt with `0 issue "letsencrypt.org"`.

If `vachagan.dev` uses Cloudflare DNS, keep SSL/TLS mode at **Full (strict)**. Follow the
current Mintlify custom-domain guidance before enabling proxy or redirect settings that
could interfere with certificate validation.

## Publishing workflow

1. Edit MDX, configuration, images, or styles in `docs/`.
2. Run `npm run check` and `uv run pytest tests/test_documentation.py`.
3. Open a pull request and review the local or Mintlify preview.
4. Merge into the configured production branch.
5. Confirm the deployment at [fastql.vachagan.dev](https://fastql.vachagan.dev).

Deployment credentials, Mintlify organization access, and DNS-provider credentials must
remain outside the repository.

## Useful links

- [Published FastQL documentation](https://fastql.vachagan.dev)
- [FastQL repository](https://github.com/MyGenX/FastQL)
- [Mintlify custom domains](https://www.mintlify.com/docs/customize/custom-domain)
- [Mintlify monorepo setup](https://www.mintlify.com/docs/guides/monorepo)
- [Mintlify GitHub deployment](https://www.mintlify.com/docs/deploy/github)

