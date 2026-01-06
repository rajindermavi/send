from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from send.credentials import GoogleAPIConfig, KeyPolicy, MSalConfig, SecureConfig

from send.common.config import Backend


class EmailClient:
    def __init__(
        self,
        *,
        msal_config: Mapping[str, Any] | None = None,
        google_api_config: Mapping[str, Any] | None = None,
        key_policy: Mapping[str, Any] | None = None,
        backend: Backend | None = None,
        passphrase: str | bytes | None = None,
    ) -> None:

        self.msal_config: MSalConfig | None = None
        self.google_api_config: GoogleAPIConfig | None = None
        self.backend: Backend | None = None
        self._passphrase = passphrase

        self.key_policy: KeyPolicy = self.update_key_policy(key_policy)
        self.secure_config = SecureConfig(
            key_policy=self.key_policy,
            passphrase=self._passphrase,
        )

        if msal_config:
            self.update_msal(msal_config)
        if google_api_config:
            self.update_google_api(google_api_config)
        self.update_backend(backend)

    def update_msal(
        self, config: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> MSalConfig:
        data: dict[str, Any] = {}
        if config:
            data.update(config)
        data.update(kwargs)

        email_address = data.get("email_address")
        if not email_address:
            raise ValueError("Missing required MSAL config field: email_address")

        token_timestamp = self._parse_datetime(data.get("token_timestamp"))
        smtp_port_value = data.get("smtp_port", data.get("port"))
        smtp_starttls_value = data.get("smtp_starttls", data.get("starttls"))

        msal_config = MSalConfig(
            email_address=str(email_address),
            client_id=data.get("client_id"),
            authority=str(data.get("authority", "organization")),
            username=data.get("username"),
            smtp_host=data.get("smtp_host") or data.get("host"),
            smtp_port=int(smtp_port_value) if smtp_port_value is not None else None,
            smtp_starttls=self._coerce_bool(smtp_starttls_value),
            token_value=data.get("token_value"),
            token_timestamp=token_timestamp,
        )
        self.msal_config = msal_config
        return msal_config

    def update_google_api(
        self, config: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> GoogleAPIConfig:
        data: dict[str, Any] = {}
        if config:
            data.update(config)
        data.update(kwargs)

        email_address = data.get("email_address")
        if not email_address:
            raise ValueError("Missing required Google API config field: email_address")

        token_timestamp = self._parse_datetime(data.get("token_timestamp"))
        port_value = data.get("port", GoogleAPIConfig.port)

        google_api_config = GoogleAPIConfig(
            email_address=str(email_address),
            client_id=data.get("client_id"),
            host=str(data.get("host") or GoogleAPIConfig.host),
            port=int(port_value) if port_value is not None else GoogleAPIConfig.port,
            scopes=self._normalize_scopes(data.get("scopes")),
            token_value=data.get("token_value"),
            token_timestamp=token_timestamp,
        )
        self.google_api_config = google_api_config
        return google_api_config

    def update_key_policy(
        self, policy: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> KeyPolicy:
        data: dict[str, Any] = {}
        if policy:
            data.update(policy)
        data.update(kwargs)

        prefer_keyring = self._coerce_bool(data.get("prefer_keyring"))
        if prefer_keyring is None:
            prefer_keyring = True
        allow_passphrase_fallback = self._coerce_bool(data.get("allow_passphrase_fallback"))
        if allow_passphrase_fallback is None:
            allow_passphrase_fallback = False

        self.key_policy = KeyPolicy(
            prefer_keyring=prefer_keyring,
            allow_passphrase_fallback=allow_passphrase_fallback,
        )
        if hasattr(self, "secure_config"):
            self.secure_config = SecureConfig(
                key_policy=self.key_policy,
                passphrase=self._passphrase,
            )
        return self.key_policy

    def update_backend(self, backend: Backend | None = None) -> Backend | None:
        if backend is not None:
            allowed_backends: set[str] = set(Backend)
            if backend not in allowed_backends:
                raise ValueError(f"Invalid backend: {backend}")
        self.backend = backend
        return backend

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _coerce_bool(self, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("1", "true", "yes", "y", "on"):
                return True
            if lowered in ("0", "false", "no", "n", "off"):
                return False
        return bool(value)

    def _normalize_scopes(self, scopes: Any) -> list[str] | None:
        if scopes is None:
            return None
        if isinstance(scopes, str):
            scopes = [scopes]
        return [str(scope) for scope in scopes if scope]

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if is_dataclass(value):
            return self._serialize_dataclass(value)
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items() if v is not None}
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        return value

    def _serialize_dataclass(self, obj: Any) -> dict[str, Any]:
        serialized = {}
        for key, value in asdict(obj).items():
            if value is None:
                continue
            serialized[key] = self._serialize_value(value)
        return serialized

    def _store_config(self) -> dict[str, Any]:
        """Stores all config and input data using SecureConfig object."""
        existing = self.secure_config.load() if self.secure_config else {}
        new_data: dict[str, Any] = {}

        if self.backend:
            new_data["backend"] = self.backend

        if self.key_policy:
            new_data["key_policy"] = self._serialize_dataclass(self.key_policy)

        if self.msal_config:
            msal_dict = self._serialize_dataclass(self.msal_config)
            new_data["msal_config"] = msal_dict
            if msal_dict.get("client_id"):
                new_data["client_id"] = msal_dict["client_id"]
            if msal_dict.get("email_address"):
                new_data["ms_email_address"] = msal_dict["email_address"]
            if msal_dict.get("authority"):
                new_data["ms_authority"] = msal_dict["authority"]

        if self.google_api_config:
            google_dict = self._serialize_dataclass(self.google_api_config)
            new_data["google_api_config"] = google_dict
            if google_dict.get("client_id"):
                new_data["google_client_id"] = google_dict["client_id"]
            if google_dict.get("email_address"):
                new_data["google_email_address"] = google_dict["email_address"]

        if not new_data:
            raise ValueError("No configuration available to store.")

        merged = existing or {}
        merged.update(new_data)
        self.secure_config.save(merged)
        return merged

    def send(
        self,
        to: list[str],
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        attachments: list[Path] | None = None,
    ):
        attachments = attachments or []
        pass
