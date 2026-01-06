from __future__ import annotations

import base64
from email.message import EmailMessage
from email.parser import BytesParser
from typing import Any, Dict, Optional

import requests

from send.auth.google_device_code import DEFAULT_SCOPES, GoogleDeviceCodeTokenProvider
from send.credentials.store import SecureConfig
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
        token_provider: Optional[GoogleDeviceCodeTokenProvider] = None,
        interactive: bool = True,
        secure_config: SecureConfig | None = None,
    ) -> "GoogleTransport":
        google_cfg = cfg.get("google_api_config") if isinstance(cfg, dict) else None
        email_address = cls._extract_email(cfg, google_cfg)
        client_id = cls._extract_client_id(cfg, google_cfg)
        client_secret = cls._extract_client_secret(cfg, google_cfg)
        scopes = cls._extract_scopes(cfg, google_cfg) or DEFAULT_SCOPES
        host = cls._extract_host(cfg, google_cfg)

        if not email_address:
            raise ValueError("Google email address is required to send mail via Gmail API.")

        if token_provider is None:
            token_provider = GoogleDeviceCodeTokenProvider(
                secure_config=secure_config,
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
            )

        access_token = token_provider.acquire_token(
            interactive=interactive,
            scopes=scopes,
        )

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
        token_provider: Optional[GoogleDeviceCodeTokenProvider] = None,
        interactive: bool = True,
        secure_config: SecureConfig | None = None,
    ) -> None:
        if not cfg:
            raise ValueError("Missing configuration for Google API send.")

        transport = cls.connect_with_oauth(
            cfg,
            token_provider,
            interactive=interactive,
            secure_config=secure_config,
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

    @staticmethod
    def _extract_client_id(cfg: Dict, google_cfg: dict | None) -> str | None:
        if not isinstance(cfg, dict):
            return None
        client_id = cfg.get("google_client_id") or cfg.get("client_id")
        if client_id:
            return str(client_id)
        if isinstance(google_cfg, dict):
            nested = google_cfg.get("client_id")
            if nested:
                return str(nested)
        return None

    @staticmethod
    def _extract_client_secret(cfg: Dict, google_cfg: dict | None) -> str | None:
        if not isinstance(cfg, dict):
            return None
        secret = cfg.get("google_client_secret")
        if secret:
            return str(secret)
        if isinstance(google_cfg, dict):
            nested = google_cfg.get("client_secret")
            if nested:
                return str(nested)
        return None

    @staticmethod
    def _extract_scopes(cfg: Dict, google_cfg: dict | None) -> list[str] | None:
        scopes: Any = None
        if isinstance(cfg, dict):
            scopes = cfg.get("scopes")
        if scopes is None and isinstance(google_cfg, dict):
            scopes = google_cfg.get("scopes")
        if scopes is None:
            return None
        if isinstance(scopes, str):
            scopes = [scope.strip() for scope in scopes.split(" ") if scope.strip()]
        return [str(scope) for scope in scopes if scope]

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
