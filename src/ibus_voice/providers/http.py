from __future__ import annotations

from dataclasses import dataclass
import json
import uuid
from typing import Protocol
from urllib import request


class HttpTransport(Protocol):
    def post_json(self, url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict: ...

    def post_multipart(
        self,
        url: str,
        headers: dict[str, str],
        fields: dict[str, str],
        files: dict[str, tuple[str, str, bytes]],
        timeout: float,
    ) -> dict: ...


@dataclass(slots=True)
class UrllibTransport:
    def post_json(self, url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, data=body, headers={**headers, "Content-Type": "application/json"})
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_multipart(
        self,
        url: str,
        headers: dict[str, str],
        fields: dict[str, str],
        files: dict[str, tuple[str, str, bytes]],
        timeout: float,
    ) -> dict:
        boundary = f"ibusvoice-{uuid.uuid4().hex}"
        body = _encode_multipart(boundary, fields, files)
        req = request.Request(
            url=url,
            data=body,
            headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def _encode_multipart(
    boundary: str,
    fields: dict[str, str],
    files: dict[str, tuple[str, str, bytes]],
) -> bytes:
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.extend(
            [
                f"--{boundary}".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"),
                b"",
                value.encode("utf-8"),
            ]
        )
    for name, (filename, mime_type, content) in files.items():
        lines.extend(
            [
                f"--{boundary}".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'
                ).encode("utf-8"),
                f"Content-Type: {mime_type}".encode("utf-8"),
                b"",
                content,
            ]
        )
    lines.append(f"--{boundary}--".encode("utf-8"))
    lines.append(b"")
    return b"\r\n".join(lines)
