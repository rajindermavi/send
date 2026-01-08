from __future__ import annotations

import base64
from email.message import EmailMessage
from email.parser import BytesParser
from typing import Dict

import requests

from send.logging import get_logger

logger = get_logger(__name__)


class GoogleTransport:
    """
    Sends email via the Gmail API using an OAuth access token.
    """

    SEND_PATH = "/gmail/v1/users/me/messages/send"
    DEFAULT_HOST = "gmail.googleapis.com"

    def __init__(self, access_token: str, from_address: str, host: str | None = None) -> None:
        self._access_token = access_token
        self._from_address = from_address
        self._host = host or self.DEFAULT_HOST
        self._send_url = f"https://{self._host}{self.SEND_PATH}"

    def send_email(self, msg: EmailMessage) -> None:
        prepared = self._ensure_from(msg)
        raw_message = base64.urlsafe_b64encode(prepared.as_bytes()).decode("ascii")

        resp = requests.post(
            self._send_url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw_message},
            timeout=30,
        )

        if resp.status_code not in (200, 202):
            raise RuntimeError(f"Gmail send failed: {resp.status_code} {resp.text}")

    def _ensure_from(self, msg: EmailMessage) -> EmailMessage:
        """
        Make sure the outbound message has a From header without mutating the original.
        """
        if msg.get("From"):
            return msg
        clone = self._clone_message(msg)
        clone["From"] = self._from_address
        return clone

    def _clone_message(self, msg: EmailMessage) -> EmailMessage:
        parser = BytesParser(policy=msg.policy)
        return parser.parsebytes(msg.as_bytes())

    @classmethod
    def connect_with_oauth(
        cls,
        cfg: Dict,
        *,
        access_token: str | None = None,
    ) -> "GoogleTransport":
        google_cfg = cfg.get("google_api_config") if isinstance(cfg, dict) else None
        email_address = cls._extract_email(cfg, google_cfg)
        host = cls._extract_host(cfg, google_cfg)

        if not email_address:
            raise ValueError("Google email address is required to send mail via Gmail API.")

        if not access_token:
            raise ValueError("Google API send requires an access_token.")

        return cls(
            access_token=access_token,
            from_address=email_address,
            host=host,
        )

    @classmethod
    def send_email_from_config(
        cls,
        cfg: Dict,
        msg: EmailMessage,
        *,
        access_token: str | None = None,
    ) -> None:
        if not cfg:
            raise ValueError("Missing configuration for Google API send.")

        transport = cls.connect_with_oauth(
            cfg,
            access_token=access_token,
        )
        transport.send_email(msg)

    @staticmethod
    def _extract_email(cfg: Dict, google_cfg: dict | None) -> str | None:
        if not isinstance(cfg, dict):
            return None
        email = cfg.get("google_email_address")
        if email:
            return str(email)
        if isinstance(google_cfg, dict):
            nested = google_cfg.get("email_address")
            if nested:
                return str(nested)
        return None

    @classmethod
    def _extract_host(cls, cfg: Dict, google_cfg: dict | None) -> str:
        if isinstance(cfg, dict):
            host = cfg.get("google_api_host") or cfg.get("host")
            if host:
                return str(host)
        if isinstance(google_cfg, dict):
            nested = google_cfg.get("host")
            if nested:
                return str(nested)
        return cls.DEFAULT_HOST
