
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import mimetypes


@dataclass(slots=True)
class Attachment:
    filename: str
    content: bytes
    maintype: str
    subtype: str

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> "Attachment":
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Attachment not found: {file_path}")

        data = file_path.read_bytes()
        mime = content_type or (mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        maintype, subtype = mime.split("/", 1) if "/" in mime else (mime, "octet-stream")

        return cls(
            filename=filename or file_path.name,
            content=data,
            maintype=maintype,
            subtype=subtype,
        )

    @classmethod
    def from_bytes(
        cls,
        content: bytes,
        *,
        filename: str,
        content_type: str | None = None,
    ) -> "Attachment":
        if not filename:
            raise ValueError("Attachment filename is required when providing raw bytes.")

        mime = content_type or "application/octet-stream"
        maintype, subtype = mime.split("/", 1) if "/" in mime else (mime, "octet-stream")

        return cls(
            filename=filename,
            content=content,
            maintype=maintype,
            subtype=subtype,
        )
