import asyncio

from fastql import Field, Query, Type, build_schema, execute


@Type
class User:
    id: str
    name: str


@Query
class QueryRoot:
    @Field
    def greeting(self) -> str:
        return "Hello from FastQL"

    @Field
    def user(self, id: str) -> User:
        return User(id=id, name="Ada")


schema = build_schema(query=QueryRoot)


def run_example():
    return asyncio.run(
        execute(schema, "{ greeting user(id: \"1\") { id name } }")
    )


if __name__ == "__main__":
    result = run_example()
    assert result.errors == []
    assert result.data == {
        "greeting": "Hello from FastQL",
        "user": {"id": "1", "name": "Ada"},
    }
