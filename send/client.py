from dataclasses import asdict, is_dataclass
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, get_args
import warnings

from send.auth import GoogleDeviceCodeTokenProvider, MSalDeviceCodeTokenProvider
from send.credentials import GoogleAPIConfig, KeyPolicy, MSalConfig, SecureConfig
from send.message.builder import EmailMessageBuilder
from send.runtime.paths import resolve_dry_run_out_dir
from send.transport.send import send as dispatch_send

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
        out_dir: Path | None = None,
    ) -> None:

        self.msal_config: MSalConfig | None = None
        self.google_api_config: GoogleAPIConfig | None = None
        self.backend: Backend | None = None
        self._passphrase = passphrase
        self._out_dir = Path(out_dir) if out_dir is not None else resolve_dry_run_out_dir()

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
        port_value = data.get("port")
        if port_value is None:
            port_value = 443

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
            allow_passphrase_fallback = True

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
            allowed_backends: set[str] = set(get_args(Backend))
            if backend not in allowed_backends:
                raise ValueError(f"Invalid backend: {backend}")
        self.backend = backend
        return backend

    def device_code(
        self,
        *,
        interactive: bool = True,
        scopes: list[str] | None = None,
        show_message: Callable[[object], None] | None = None,
    ) -> str | None:
        """Run the provider-specific device-code flow for the configured backend.

        Returns the acquired access token (if any). Dry-run backends skip auth and
        emit a warning instead of raising.
        """
        if not self.backend:
            raise ValueError("Backend must be set before requesting device code.")

        config_snapshot = self._store_config()

        if self.backend == "dry_run":
            warnings.warn(
                "device_code skipped for dry_run backend; no authentication required.",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

        if self.backend == "ms_graph":
            provider = MSalDeviceCodeTokenProvider(
                secure_config=self.secure_config,
                authority=self.msal_config.authority if self.msal_config else None,
                show_message=show_message,
                client_id=self.msal_config.client_id if self.msal_config else None,
            )
            return provider.acquire_token(interactive=interactive, scopes=scopes)

        if self.backend == "google_api":
            google_scopes = scopes or (self.google_api_config.scopes if self.google_api_config else None)
            google_client_id = self.google_api_config.client_id if self.google_api_config else None
            google_client_secret = None
            google_cfg = config_snapshot.get("google_api_config") if isinstance(config_snapshot, dict) else None
            if not google_client_id and isinstance(config_snapshot, dict):
                google_client_id = config_snapshot.get("google_client_id") or config_snapshot.get("client_id")
            if isinstance(config_snapshot, dict):
                google_client_secret = config_snapshot.get("google_client_secret")
                if not google_client_secret and isinstance(google_cfg, dict):
                    google_client_secret = google_cfg.get("client_secret")

            provider = GoogleDeviceCodeTokenProvider(
                secure_config=self.secure_config,
                client_id=google_client_id,
                client_secret=google_client_secret,
                scopes=google_scopes,
                show_message=show_message,
            )
            return provider.acquire_token(interactive=interactive, scopes=google_scopes)

        raise ValueError(f"Unsupported backend: {self.backend}")

    def message(
        self,
        *,
        to: Any,
        cc: Any | None = None,
        bcc: Any | None = None,
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        attachments: list[str | Path] | None = None,
        from_address: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> EmailMessage:
        """Build an EmailMessage using EmailMessageBuilder with sensible defaults."""
        builder = EmailMessageBuilder()

        from_value = from_address or self._infer_from_address()
        if not from_value:
            raise ValueError("from_address is required when no configured email is available.")

        builder.set_from(from_value)
        builder.add_to(to)
        if cc:
            builder.add_cc(cc)
        if bcc:
            builder.add_bcc(bcc)
        if subject is not None:
            builder.set_subject(subject)
        if body_text is not None:
            builder.set_text_body(body_text)
        if body_html is not None:
            builder.set_html_body(body_html)

        for attachment in attachments or []:
            builder.add_attachment(attachment)

        for name, value in (headers or {}).items():
            builder.add_header(name, value)

        return builder.build()

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

    def _infer_from_address(self) -> str | None:
        if self.backend == "ms_graph" and self.msal_config:
            return self.msal_config.email_address
        if self.backend == "google_api" and self.google_api_config:
            return self.google_api_config.email_address
        if self.msal_config:
            return self.msal_config.email_address
        if self.google_api_config:
            return self.google_api_config.email_address
        return None

    def send(
        self,
        to: Any,
        subject: str | None = None,
        body_html: str | None = None,
        body_text: str | None = None,
        attachments: list[str | Path] | None = None,
        *,
        cc: Any | None = None,
        bcc: Any | None = None,
        from_address: str | None = None,
        headers: Mapping[str, str] | None = None,
        interactive: bool = True,
        scopes: list[str] | None = None,
        show_message: Callable[[object], None] | None = None,
        write_metadata: bool = True,
    ) -> EmailMessage:
        """Build and send an EmailMessage via the configured backend."""
        if not self.backend:
            raise ValueError("Backend must be set before sending email.")

        message = self.message(
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            from_address=from_address,
            headers=headers,
        )

        cfg = self._store_config()

        # Acquire tokens (no-op + warning for dry_run).
        access_token = self.device_code(
            interactive=interactive,
            scopes=scopes,
            show_message=show_message,
        )

        dispatch_send(
            cfg,
            message,
            self.backend,
            write_metadata=write_metadata,
            out_dir=self._out_dir,
            access_token=access_token,
        )

        return message
