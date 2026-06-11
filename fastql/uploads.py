"""Upload scalar and framework-neutral uploaded-file representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, BinaryIO, Mapping

from fastql.language import ast
from fastql.types import ScalarCoercionError, ScalarType


@dataclass
class UploadedFile:
    """A file received through the GraphQL multipart request protocol."""

    filename: str
    content_type: str
    stream: BinaryIO
    headers: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_bytes(
        cls,
        filename: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        headers: Mapping[str, str] | None = None,
    ) -> "UploadedFile":
        return cls(
            filename=filename,
            content_type=content_type,
            stream=BytesIO(content),
            headers=dict(headers or {}),
        )

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.stream.seek(offset, whence)

    def tell(self) -> int:
        return self.stream.tell()

    def close(self) -> None:
        self.stream.close()


def _parse_upload_value(value: Any) -> Any:
    if isinstance(value, UploadedFile) or callable(getattr(value, "read", None)):
        return value
    raise ScalarCoercionError("Upload values must be readable file objects.")


def _parse_upload_literal(value: ast.ValueNode) -> Any:
    raise ScalarCoercionError("Upload values must be supplied through variables.")


def _serialize_upload(value: Any) -> Any:
    raise ScalarCoercionError("Upload is an input-only scalar.")


Upload = ScalarType(
    name="Upload",
    serialize=_serialize_upload,
    parse_value=_parse_upload_value,
    parse_literal=_parse_upload_literal,
    description="A file supplied through a multipart GraphQL request.",
)


__all__ = ["Upload", "UploadedFile"]
