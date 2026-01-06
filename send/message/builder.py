from __future__ import annotations

from email.message import EmailMessage
from email.utils import formataddr, getaddresses, parseaddr
from pathlib import Path
from typing import Iterable, Self

from send.message.models import Attachment

AddressInput = str | Iterable[str]

_RESERVED_HEADERS = {"from", "to", "cc", "bcc", "subject"}


class EmailMessageBuilder:
    """
    Structured builder for email.message.EmailMessage instances.

    The builder normalizes addresses, builds multipart bodies when needed,
    and attaches files with sensible MIME type defaults.
    """

    def __init__(self) -> None:
        self._from: str | None = None
        self._to: list[str] = []
        self._cc: list[str] = []
        self._bcc: list[str] = []
        self._subject: str | None = None
        self._text_body: str | None = None
        self._html_body: str | None = None
        self._attachments: list[Attachment] = []
        self._headers: list[tuple[str, str]] = []
        self._to_seen: set[str] = set()
        self._cc_seen: set[str] = set()
        self._bcc_seen: set[str] = set()

    # ---------------
    # Address setters
    # ---------------
    def set_from(self, address: str) -> Self:
        self._from = self._normalize_single_address(address)
        return self

    def add_to(self, addresses: AddressInput) -> Self:
        self._add_recipients(self._to, self._to_seen, addresses)
        return self

    def add_cc(self, addresses: AddressInput) -> Self:
        self._add_recipients(self._cc, self._cc_seen, addresses)
        return self

    def add_bcc(self, addresses: AddressInput) -> Self:
        self._add_recipients(self._bcc, self._bcc_seen, addresses)
        return self

    # -------------
    # Content
    # -------------
    def set_subject(self, subject: str) -> Self:
        self._subject = subject.strip() if subject is not None else None
        return self

    def set_text_body(self, body: str) -> Self:
        self._text_body = body
        return self

    def set_html_body(self, body: str) -> Self:
        self._html_body = body
        return self

    # -------------
    # Attachments
    # -------------
    def add_attachment(
        self,
        path: str | Path,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> Self:
        attachment = Attachment.from_path(
            path,
            filename=filename,
            content_type=content_type,
        )
        self._attachments.append(attachment)
        return self

    def add_attachment_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str | None = None,
    ) -> Self:
        attachment = Attachment.from_bytes(
            content,
            filename=filename,
            content_type=content_type,
        )
        self._attachments.append(attachment)
        return self

    # -------------
    # Headers
    # -------------
    def add_header(self, name: str, value: str) -> Self:
        if not name:
            raise ValueError("Header name must be provided.")
        lower = name.lower()
        if lower in _RESERVED_HEADERS:
            raise ValueError(f"Header '{name}' is managed by the builder and cannot be set manually.")
        self._headers.append((name, value))
        return self

    # -------------
    # Build
    # -------------
    def build(self) -> EmailMessage:
        self._validate_required_fields()

        msg = EmailMessage()

        msg["From"] = self._from
        if self._to:
            msg["To"] = ", ".join(self._to)
        if self._cc:
            msg["Cc"] = ", ".join(self._cc)
        if self._bcc:
            msg["Bcc"] = ", ".join(self._bcc)
        if self._subject:
            msg["Subject"] = self._subject

        for name, value in self._headers:
            msg[name] = value

        # Body
        if self._text_body is not None:
            msg.set_content(self._text_body)

        if self._html_body is not None:
            if self._text_body is None:
                msg.set_content(self._html_body, subtype="html")
            else:
                msg.add_alternative(self._html_body, subtype="html")

        # Ensure there is at least one part even if the body strings were empty.
        if msg.get_body() is None and not msg.get_payload():
            msg.set_content("")

        # Attachments
        for attachment in self._attachments:
            msg.add_attachment(
                attachment.content,
                maintype=attachment.maintype,
                subtype=attachment.subtype,
                filename=attachment.filename,
            )

        return msg

    # -------------
    # helpers
    # -------------
    def _add_recipients(
        self,
        target: list[str],
        seen: set[str],
        addresses: AddressInput,
    ) -> None:
        normalized = self._normalize_addresses(addresses)
        for formatted in normalized:
            addr_only = parseaddr(formatted)[1].lower()
            if addr_only in seen:
                continue
            target.append(formatted)
            seen.add(addr_only)

    def _normalize_single_address(self, address: str) -> str:
        normalized = self._normalize_addresses(address)
        if len(normalized) != 1:
            raise ValueError("Exactly one From address must be provided.")
        return normalized[0]

    def _normalize_addresses(self, addresses: AddressInput) -> list[str]:
        if isinstance(addresses, str):
            raw = [addresses]
        else:
            raw = list(addresses)

        parsed = getaddresses(raw)
        if not parsed:
            raise ValueError("At least one email address is required.")

        normalized: list[str] = []
        seen: set[str] = set()
        for name, addr in parsed:
            addr = addr.strip()
            if not addr:
                continue
            if "@" not in addr:
                raise ValueError(f"Invalid email address: {addr}")
            addr_key = addr.lower()
            if addr_key in seen:
                continue
            seen.add(addr_key)
            normalized.append(formataddr((name, addr)) if name else addr)

        if not normalized:
            raise ValueError("At least one email address is required.")
        return normalized

    def _validate_required_fields(self) -> None:
        if not self._from:
            raise ValueError("From address must be set before building a message.")

        if not (self._to or self._cc or self._bcc):
            raise ValueError("At least one recipient (To, Cc, or Bcc) is required.")

        if self._text_body is None and self._html_body is None and not self._attachments:
            raise ValueError("Message content is empty. Provide a text or HTML body, or at least one attachment.")
