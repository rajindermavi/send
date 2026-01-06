from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MSAuthority = Literal["organization", "consumer"]


@dataclass(slots=True)
class MSalConfig:
    # Identity / API auth
    email_address: str
    client_id: str | None = None
    authority: MSAuthority = "organization"
    username: str | None = None

    # SMTP
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_starttls: bool | None = None

    # Cached token state
    token_value: str | None = None
    token_timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.authority not in ("organization", "consumer"):
            raise ValueError("authority must be 'organization' or 'consumer'")

@dataclass(slots=True)
class GoogleAPIConfig:
    email_address: str
    client_id: str | None = None
    host: str = "gmail.googleapis.com"
    port: int = 443
    scopes: list[str] | None = None

    # Cached token state
    token_value: str | None = None
    token_timestamp: datetime | None = None

@dataclass(slots=True)
class TokenRecord:
    access_token: str
    expires_at: datetime

@dataclass(frozen=True)
class KeyPolicy:
    prefer_keyring: bool = True
    allow_passphrase_fallback: bool = False
