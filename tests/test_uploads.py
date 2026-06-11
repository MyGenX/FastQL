"""Upload scalar and graphql-multipart-request-spec tests."""

from __future__ import annotations

import json

import pytest

from fastql import Field, Mutation, Query, Schema, Upload, UploadedFile
from fastql.context import default_dependencies
from fastql.decorators import default_registry
from fastql.integrations import GraphQLHTTPHandler, HTTPRequest


@pytest.fixture(autouse=True)
def clear_registries():
    default_registry.clear()
    default_dependencies.clear()


def make_schema():
    @Query
    class Q:
        @Field
        def ping(self) -> str:
            return "pong"

    @Mutation
    class M:
        @Field
        def upload(self, file: Upload) -> str:
            content = file.read().decode("utf-8")
            return f"{file.filename}|{file.content_type}|{content}"

        @Field
        def upload_many(self, files: list[Upload]) -> list[str]:
            return [
                f"{file.filename}:{file.read().decode('utf-8')}"
                for file in files
            ]

    return Schema(query=Q, mutation=M)


def multipart_request(
    operations,
    file_map,
    files: dict[str, tuple[str, str, bytes]],
    *,
    boundary: str = "fastql-boundary",
) -> HTTPRequest:
    parts = []

    def field(name: str, value: str) -> None:
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )

    field("operations", json.dumps(operations))
    field("map", json.dumps(file_map))
    for name, (filename, content_type, content) in files.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                content,
                b"\r\n",
            ]
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return HTTPRequest(
        "POST",
        "/graphql",
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        body=b"".join(parts),
    )


def test_upload_scalar_is_input_type_and_file_is_readable():
    schema = make_schema()
    upload_argument = schema.mutation.fields["upload"].args["file"].type
    assert upload_argument.of_type.name == "Upload"

    file = UploadedFile.from_bytes(
        "hello.txt", b"hello", content_type="text/plain"
    )
    assert file.filename == "hello.txt"
    assert file.content_type == "text/plain"
    assert file.read() == b"hello"


async def test_single_file_is_mapped_into_variables():
    request = multipart_request(
        {
            "query": "mutation($file: Upload!) { upload(file: $file) }",
            "variables": {"file": None},
        },
        {"0": ["variables.file"]},
        {"0": ("hello.txt", "text/plain", b"hello")},
    )
    response = await GraphQLHTTPHandler(make_schema()).handle(request)

    assert response.status == 200
    assert json.loads(response.body) == {
        "data": {"upload": "hello.txt|text/plain|hello"}
    }


async def test_multiple_files_are_mapped_into_list_variable():
    request = multipart_request(
        {
            "query": "mutation($files: [Upload!]!) { uploadMany(files: $files) }",
            "variables": {"files": [None, None]},
        },
        {
            "first": ["variables.files.0"],
            "second": ["variables.files.1"],
        },
        {
            "first": ("a.txt", "text/plain", b"A"),
            "second": ("b.txt", "text/plain", b"B"),
        },
    )
    response = await GraphQLHTTPHandler(make_schema()).handle(request)

    assert response.status == 200
    assert json.loads(response.body) == {
        "data": {"uploadMany": ["a.txt:A", "b.txt:B"]}
    }


async def test_file_can_be_mapped_into_batched_operations():
    request = multipart_request(
        [
            {
                "query": "mutation($file: Upload!) { upload(file: $file) }",
                "variables": {"file": None},
            },
            {"query": "{ ping }"},
        ],
        {"0": ["0.variables.file"]},
        {"0": ("batch.txt", "text/plain", b"batched")},
    )
    response = await GraphQLHTTPHandler(
        make_schema(), allow_batching=True
    ).handle(request)

    assert response.status == 200
    assert json.loads(response.body) == [
        {"data": {"upload": "batch.txt|text/plain|batched"}},
        {"data": {"ping": "pong"}},
    ]


@pytest.mark.parametrize(
    "file_map",
    [
        {"missing": ["variables.file"]},
        {"0": ["variables.nope"]},
        {"0": ["variables.file.name"]},
    ],
)
async def test_malformed_file_map_is_rejected(file_map):
    request = multipart_request(
        {
            "query": "mutation($file: Upload!) { upload(file: $file) }",
            "variables": {"file": None},
        },
        file_map,
        {"0": ("hello.txt", "text/plain", b"hello")},
    )
    response = await GraphQLHTTPHandler(make_schema()).handle(request)

    assert response.status == 400
    assert "errors" in json.loads(response.body)
