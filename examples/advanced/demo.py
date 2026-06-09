"""Run the Phase 2 cookbook with ``python -m examples.advanced.demo``."""

from __future__ import annotations

import asyncio

from fastql import execute, print_schema
from fastql.relay import offset_to_cursor, to_global_id

from examples.advanced.generics import schema as generics_schema
from examples.advanced.relay import register_nodes, schema as relay_schema
from examples.advanced.schema_metadata import schema as metadata_schema


async def main() -> None:
    print("== generics ==")
    result = await execute(
        generics_schema,
        "{ users { total items { name } } posts { total items { title } } }",
    )
    print(result.data)

    print("\n== relay ==")
    register_nodes()
    global_id = to_global_id("RelayUser", 2)
    after = offset_to_cursor(0)
    result = await execute(
        relay_schema,
        '{ node(id: "%s") { __typename ... on RelayUser { name } } '
        'users(first: 2, after: "%s") {'
        " edges { cursor node { id name } } pageInfo { hasNextPage } } }"
        % (global_id, after),
    )
    print(result.data)

    print("\n== directives, visibility, and enums ==")
    result = await execute(metadata_schema, "{ product { availability label } }")
    print(result.data)
    print(print_schema(metadata_schema))


if __name__ == "__main__":
    asyncio.run(main())

