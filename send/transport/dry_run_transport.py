from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from email.message import EmailMessage
from typing import Iterable

from send.logging import get_logger

logger = get_logger(__name__)


class DryRunTransport:
    """
    A no-op email transport that records messages to disk instead of sending them.

    - Writes a .eml file containing the full MIME message
    - Optionally writes a JSON metadata sidecar
    - Performs no network calls
    - Does not mutate the EmailMessage
    """

    def __init__(
        self,
        out_dir: Path,
        write_metadata: bool = True,
    ) -> None:
        self.out_dir = out_dir
        self.write_metadata = write_metadata

        self.out_dir.mkdir(parents=True, exist_ok=True)

    def send_email_from_config(self, msg: EmailMessage,**kw) -> None:
        timestamp = datetime.now(timezone.utc)
        uid = uuid.uuid4().hex

        stem = f"{timestamp.strftime('%Y-%m-%dT%H-%M-%S')}_{uid}"
        eml_path = self.out_dir / f"{stem}.eml"

        # Write raw RFC 5322 message
        with eml_path.open("wb") as f:
            f.write(msg.as_bytes())

        if self.write_metadata:
            meta_path = self.out_dir / f"{stem}.json"
            meta_path.write_text(
                json.dumps(
                    self._build_metadata(msg, timestamp),
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

        logger.info(
            "DRY RUN: wrote email to %s (to=%s, subject=%r)",
            eml_path,
            self._get_recipients(msg, "To"),
            msg.get("Subject"),
        )

    # -------------------------
    # helpers
    # -------------------------

    def _build_metadata(self, msg: EmailMessage, timestamp: datetime) -> dict:
        attachments = list(self._iter_attachments(msg))

        return {
            "backend": "DRY_RUN",
            "timestamp": timestamp.isoformat(),
            "from": msg.get("From"),
            "to": self._get_recipients(msg, "To"),
            "cc": self._get_recipients(msg, "Cc"),
            "bcc": self._get_recipients(msg, "Bcc"),
            "subject": msg.get("Subject"),
            "attachment_count": len(attachments),
            "attachments": [
                {
                    "filename": part.get_filename(),
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b""),
                }
                for part in attachments
            ],
        }

    def _get_recipients(self, msg: EmailMessage, header: str) -> list[str]:
        value = msg.get(header)
        if not value:
            return []
        # Keep this simple; parsing belongs elsewhere
        return [addr.strip() for addr in value.split(",")]

    def _iter_attachments(self, msg: EmailMessage) -> Iterable[EmailMessage]:
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                yield part
