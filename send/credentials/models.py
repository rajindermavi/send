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
    host: str
    port: int
    
    email_address: str
    client_id: str | None = None

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