from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import sys
from typing import Any

from cryptography.fernet import Fernet

from send.credentials.models import KeyPolicy
from send.credentials.paths import get_encrypted_config_path
from send.runtime.context import get_runtime_context
from send.runtime.paths import AppPaths, resolve_paths

LIB_NAME = "SEND"
KEYRING_SERVICE = LIB_NAME
KEYRING_USERNAME = "config_key"

class SecureConfig:
    def __init__(
        self,
        *,
        paths: AppPaths | None = None,
        key_policy: KeyPolicy | None = None,
        passphrase: str | bytes | None = None,
    ):
        self._win32crypt: Any | None = None
        self._use_dpapi = self._init_dpapi()
        self._fernet: Fernet | None = None
        self._key_storage: str | None = None
        self._policy = key_policy or KeyPolicy()
        self._passphrase = passphrase
        self._warned_keyring_unavailable = False
        self._keyring_available = False
        if self._policy.prefer_keyring:
            self._keyring_available, keyring_reason = self._check_keyring_available()
            if not self._keyring_available:
                self._enable_passphrase_fallback(keyring_reason)

        self._paths = (paths or resolve_paths(get_runtime_context(app_name=LIB_NAME))).ensure()
        self._config_path = get_encrypted_config_path(self._paths)

        self._log(f"Config path: {self._config_path}")
        self._log(f"DPAPI enabled: {self._use_dpapi}")

    def _log(self, message: str) -> None:
        print(f"[SecureConfig] {message}")

    def _check_keyring_available(self) -> tuple[bool, str]:
        try:
            import keyring  # type: ignore
        except Exception:
            return False, "keyring module not available"
        try:
            backend = keyring.get_keyring()
        except Exception:
            return False, "keyring backend unavailable"
        try:
            priority = getattr(backend, "priority", None)
        except Exception:
            return False, "keyring backend unavailable"
        if priority is not None and priority <= 0:
            return False, "no recommended keyring backend"
        if not hasattr(backend, "get_password") or not hasattr(backend, "set_password"):
            return False, "keyring backend missing required methods"
        return True, ""

    def _enable_passphrase_fallback(self, reason: str) -> None:
        if not self._warned_keyring_unavailable:
            reason_text = f" ({reason})" if reason else ""
            self._log(f"WARNING: Keyring unavailable{reason_text}; enabling passphrase fallback.")
            self._warned_keyring_unavailable = True
        if not self._policy.allow_passphrase_fallback:
            self._policy = KeyPolicy(
                prefer_keyring=self._policy.prefer_keyring,
                allow_passphrase_fallback=True,
            )

    def _disable_keyring(self, reason: str) -> None:
        self._keyring_available = False
        if self._policy.prefer_keyring:
            self._enable_passphrase_fallback(reason)

    def _init_dpapi(self) -> bool:
        """
        Try to enable DPAPI when on Windows. Falls back if unavailable.
        """
        if os.name != "nt":
            return False
        try:
            import win32crypt  # type: ignore
        except Exception:
            return False

        self._win32crypt = win32crypt
        return True

    def _get_keyring(self):
        if not self._keyring_available:
            return None
        try:
            import keyring  # type: ignore
        except Exception:
            self._disable_keyring("keyring module not available")
            return None
        return keyring

    def _load_key_from_keyring(self) -> bytes | None:
        keyring = self._get_keyring()
        if not keyring:
            return None
        try:
            stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception:
            self._disable_keyring("keyring lookup failed")
            return None
        if not stored:
            self._log("No key found in keyring.")
            return None
        try:
            self._log("Loaded key from keyring.")
            self._key_storage = "keyring"
            return stored.encode("utf-8")
        except Exception:
            self._disable_keyring("keyring data could not be decoded")
            return None

    def _save_key_to_keyring(self, key: bytes) -> bool:
        keyring = self._get_keyring()
        if not keyring:
            return False
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, key.decode("utf-8"))
            self._log("Saved key to keyring.")
            return True
        except Exception:
            self._disable_keyring("keyring write failed")
            return False

    def _ensure_fernet(self) -> Fernet:
        if self._fernet is None:
            key = self._load_or_generate_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _derive_key_from_passphrase(self, passphrase: str | bytes) -> bytes:
        if isinstance(passphrase, str):
            passphrase_bytes = passphrase.encode("utf-8")
        else:
            passphrase_bytes = passphrase
        salt = b"SEND_SECURECONFIG_V1"
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            passphrase_bytes,
            salt,
            390_000,
            dklen=32,
        )
        return base64.urlsafe_b64encode(derived)

    def _get_passphrase(self) -> str | bytes | None:
        if self._passphrase is not None:
            return self._passphrase
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return None
        try:
            entered = getpass.getpass("Enter passphrase to encrypt credentials: ")
        except (EOFError, KeyboardInterrupt):
            return None
        if not entered:
            return None
        self._passphrase = entered
        return self._passphrase

    def _load_or_generate_key(self) -> bytes:
        # Prefer OS keyring so secrets are not written to disk.
        keyring_key: bytes | None = None
        if self._policy.prefer_keyring and self._keyring_available:
            keyring_key = self._load_key_from_keyring()
        if keyring_key:
            return keyring_key

        if self._policy.prefer_keyring and self._keyring_available:
            key = Fernet.generate_key()
            self._log("Generated new Fernet key.")
            if self._save_key_to_keyring(key):
                self._key_storage = "keyring"
                return key
            if not self._policy.allow_passphrase_fallback:
                raise RuntimeError("Keyring unavailable and passphrase fallback disabled by policy.")

        if not self._policy.allow_passphrase_fallback:
            raise RuntimeError("No valid key source available (keyring disabled and no passphrase allowed).")

        passphrase = self._get_passphrase()
        if passphrase is None:
            raise RuntimeError("Passphrase is required to derive encryption key when keyring cannot be used.")

        key = self._derive_key_from_passphrase(passphrase)
        self._key_storage = "passphrase"
        return key

    def _dpapi_decrypt(self, data: bytes) -> bytes | None:
        if not self._win32crypt:
            return None
        try:
            return self._win32crypt.CryptUnprotectData(data, None, None, None, 0)[1]
        except Exception:
            self._use_dpapi = False
            return None

    def _dpapi_encrypt(self, data: bytes) -> bytes | None:
        if not self._win32crypt:
            return None
        try:
            encrypted = self._win32crypt.CryptProtectData(data, None, None, None, None, 0)[1]
        except Exception:
            self._use_dpapi = False
            return None

        if isinstance(encrypted, memoryview):
            return encrypted.tobytes()
        if isinstance(encrypted, (bytes, bytearray)):
            return bytes(encrypted)

        # Unexpected type; disable DPAPI so we fall back to Fernet.
        self._use_dpapi = False
        return None

    def load(self) -> dict:
        """Decrypt and load the config from config.enc."""
        cfg_file = self._config_path
        if not cfg_file.exists():
            return {}  # no config yet

        encrypted = cfg_file.read_bytes()

        if self._use_dpapi:
            decrypted = self._dpapi_decrypt(encrypted)
            if decrypted is not None:
                self._log(f"Loaded config via DPAPI from: {cfg_file}")
                try:
                    return json.loads(decrypted.decode("utf-8"))
                except Exception:
                    return {}

        fernet = self._ensure_fernet()
        try:
            decrypted = fernet.decrypt(encrypted)
        except Exception:
            # If corrupt, return empty (or raise)
            return {}

        self._log(f"Loaded config via Fernet from: {cfg_file}")
        return json.loads(decrypted.decode("utf-8"))

    def save(self, config_dict: dict) -> None:
        """Encrypt and save the config as JSON."""
        json_bytes = json.dumps(config_dict, indent=2).encode("utf-8")
        cfg_file = self._config_path

        if self._use_dpapi:
            encrypted = self._dpapi_encrypt(json_bytes)
            if encrypted is not None:
                self._log(f"Saving config with DPAPI to: {cfg_file}")
                cfg_file.write_bytes(encrypted)
                self._announce_encryption_status()
                return

        fernet = self._ensure_fernet()
        encrypted = fernet.encrypt(json_bytes)
        self._log(f"Saving config with Fernet to: {cfg_file}")
        cfg_file.write_bytes(encrypted)
        self._announce_encryption_status()

    def _announce_encryption_status(self) -> None:
        """
        Inform the user how the encryption key is stored and confirm encryption.
        """
        if self._use_dpapi and self._key_storage is None:
            self._log("Config protected with Windows DPAPI; no separate key file used.")
        elif self._key_storage == "keyring":
            self._log("Encryption key stored in system keyring.")
        elif self._key_storage == "passphrase":
            self._log("Encryption key derived from user-supplied passphrase (not persisted).")
        else:
            self._log("Encryption key storage location unknown.")
        msg = "All data securely encrypted!"
        print(msg)

    def is_keyring_backed(self) -> bool:
        """Return True if the encryption key is persisted in the OS keyring."""
        return self._key_storage == "keyring"
