"""Per-framework example projects.

Each subpackage mounts the same :data:`examples.app.schema` on a different web
framework with only a few lines of glue, proving the FastQL core is framework-agnostic.
The per-request authentication logic is shared in :mod:`examples.projects._auth`; only
the (framework-specific) header extraction differs between projects.
"""
