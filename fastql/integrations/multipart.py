"""graphql-multipart-request-spec parsing using the Python standard library."""

from __future__ import annotations

import json
from email import policy
from email.parser import BytesParser
from typing import Any

from fastql.uploads import UploadedFile


class MultipartRequestError(ValueError):
    """Raised when a GraphQL multipart request is malformed."""


def parse_multipart_request(content_type: str, body: bytes) -> Any:
    """Parse and map a GraphQL multipart request into operation payloads."""
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: "
        + content_type.encode("latin-1")
        + b"\r\nMIME-Version: 1.0\r\n\r\n"
        + body
    )
    if not message.is_multipart():
        raise MultipartRequestError("Multipart request has no valid boundary.")

    fields: dict[str, str] = {}
    files: dict[str, UploadedFile] = {}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not isinstance(name, str) or not name:
            raise MultipartRequestError("Multipart part is missing its field name.")
        if name in fields or name in files:
            raise MultipartRequestError(f"Duplicate multipart field {name!r}.")
        content = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename is None:
            charset = part.get_content_charset() or "utf-8"
            try:
                fields[name] = content.decode(charset)
            except (LookupError, UnicodeDecodeError) as error:
                raise MultipartRequestError(
                    f"Multipart field {name!r} is not valid text."
                ) from error
            continue
        files[name] = UploadedFile.from_bytes(
            filename,
            content,
            content_type=part.get_content_type() or "application/octet-stream",
            headers={key.lower(): value for key, value in part.items()},
        )

    operations = _json_field(fields, "operations")
    file_map = _json_field(fields, "map")
    if not isinstance(operations, (dict, list)):
        raise MultipartRequestError(
            "Multipart 'operations' must be an object or array."
        )
    if not isinstance(file_map, dict):
        raise MultipartRequestError("Multipart 'map' must be an object.")

    for file_key, paths in file_map.items():
        if not isinstance(file_key, str) or file_key not in files:
            raise MultipartRequestError(
                f"Multipart map references missing file field {file_key!r}."
            )
        if not isinstance(paths, list) or not paths:
            raise MultipartRequestError(
                f"Multipart map entry {file_key!r} must contain paths."
            )
        for path in paths:
            if not isinstance(path, str) or not path:
                raise MultipartRequestError("Multipart map paths must be strings.")
            _replace_placeholder(operations, path, files[file_key])
    return operations


def _json_field(fields: dict[str, str], name: str) -> Any:
    value = fields.get(name)
    if value is None:
        raise MultipartRequestError(f"Multipart request is missing {name!r}.")
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise MultipartRequestError(
            f"Multipart field {name!r} is not valid JSON."
        ) from error


def _replace_placeholder(root: Any, path: str, file: UploadedFile) -> None:
    segments = path.split(".")
    current = root
    for segment in segments[:-1]:
        current = _path_value(current, segment, path)
    final = segments[-1]
    if isinstance(current, dict):
        if final not in current or current[final] is not None:
            raise MultipartRequestError(
                f"Multipart map path {path!r} does not reference a null placeholder."
            )
        current[final] = file
        return
    if isinstance(current, list):
        index = _list_index(final, len(current), path)
        if current[index] is not None:
            raise MultipartRequestError(
                f"Multipart map path {path!r} does not reference a null placeholder."
            )
        current[index] = file
        return
    raise MultipartRequestError(f"Multipart map path {path!r} does not exist.")


def _path_value(current: Any, segment: str, path: str) -> Any:
    if isinstance(current, dict):
        if segment not in current:
            raise MultipartRequestError(
                f"Multipart map path {path!r} does not exist."
            )
        return current[segment]
    if isinstance(current, list):
        return current[_list_index(segment, len(current), path)]
    raise MultipartRequestError(f"Multipart map path {path!r} does not exist.")


def _list_index(segment: str, size: int, path: str) -> int:
    try:
        index = int(segment)
    except ValueError as error:
        raise MultipartRequestError(
            f"Multipart map path {path!r} has an invalid list index."
        ) from error
    if index < 0 or index >= size:
        raise MultipartRequestError(f"Multipart map path {path!r} does not exist.")
    return index


__all__ = ["MultipartRequestError", "parse_multipart_request"]
