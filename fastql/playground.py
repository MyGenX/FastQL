"""The GraphiQL in-browser IDE page served by the dev server.

Loads GraphiQL from a CDN and points its fetcher at the server's GraphQL
endpoint path. Requires internet access at runtime; the schema endpoints
(``/schema.graphql``, ``/schema.json``) work offline.
"""

from __future__ import annotations

# GraphiQL is pinned to the 3.x line: it ships a UMD build that exposes the
# global `GraphiQL` (with `createFetcher`) used below. The unversioned URL now
# resolves to 5.x, which is ESM-only (no global) and breaks this loader.
_GRAPHIQL_VERSION = "3"
_REACT_VERSION = "18"

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>FastQL · GraphiQL</title>
    <link
      rel="stylesheet"
      href="https://unpkg.com/graphiql@__GRAPHIQL__/graphiql.min.css"
    />
    <style>
      html, body, #graphiql { height: 100%; margin: 0; width: 100%; }
    </style>
  </head>
  <body>
    <div id="graphiql">Loading GraphiQL…</div>
    <script
      crossorigin
      src="https://unpkg.com/react@__REACT__/umd/react.production.min.js"
    ></script>
    <script
      crossorigin
      src="https://unpkg.com/react-dom@__REACT__/umd/react-dom.production.min.js"
    ></script>
    <script
      crossorigin
      src="https://unpkg.com/graphiql@__GRAPHIQL__/graphiql.min.js"
    ></script>
    <script>
      const fetcher = GraphiQL.createFetcher({ url: "__ENDPOINT__" });
      const root = ReactDOM.createRoot(document.getElementById("graphiql"));
      root.render(React.createElement(GraphiQL, { fetcher }));
    </script>
  </body>
</html>
"""


def playground_html(endpoint_path: str = "/graphql") -> str:
    """Return the GraphiQL HTML page wired to ``endpoint_path``."""
    return (
        _TEMPLATE.replace("__GRAPHIQL__", _GRAPHIQL_VERSION)
        .replace("__REACT__", _REACT_VERSION)
        .replace("__ENDPOINT__", endpoint_path)
    )


__all__ = ["playground_html"]
