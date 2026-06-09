"""Generic type synthesis with one reusable ``Page[T]`` definition."""

from __future__ import annotations

from typing import Generic, TypeVar

from fastql import Field, Schema, Type, TypeRegistry

T = TypeVar("T")


@Type
class User:
    id: int
    name: str


@Type
class Post:
    id: int
    title: str


@Type
class Page(Generic[T]):
    total: int
    items: list[T]


USERS = [User(1, "Ada"), User(2, "Grace")]
POSTS = [Post(10, "Analytical Engine"), Post(20, "The First Compiler")]


@Type(name="Query")
class Queries:
    @Field
    def users(self) -> Page[User]:
        return Page(total=len(USERS), items=USERS)

    @Field
    def posts(self) -> Page[Post]:
        return Page(total=len(POSTS), items=POSTS)


registry = TypeRegistry()
for type_ in (User, Post, Queries):
    registry.register_type(type_, type_.__fastql_type__)
registry.generic_templates[Page] = Page.__fastql_generic__

schema = Schema(query=Queries, registry=registry)

__all__ = ["Page", "Post", "Queries", "User", "schema"]
