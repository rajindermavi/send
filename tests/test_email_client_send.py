from email.message import EmailMessage

import pytest

from send.client import EmailClient


class DummySecureConfig:
    def __init__(self, initial: dict | None = None) -> None:
        self._data = dict(initial or {})
        self.saved: list[dict] = []

    def load(self) -> dict:
        return dict(self._data)

    def save(self, data: dict) -> None:
        self.saved.append(dict(data))
        self._data = dict(data)


def test_send_runs_device_code_and_dispatch(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path))

    client = EmailClient(
        msal_config={
            "email_address": "ms-user@example.com",
            "client_id": "client-123",
            "authority": "organization",
        },
        backend="ms_graph",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )
    client.secure_config = DummySecureConfig()

    captured: dict = {}

    def fake_device_code(**kwargs):
        captured["device_code"] = kwargs
        return "token-xyz"

    def fake_dispatch(cfg, msg, backend, **kwargs):
        captured["dispatch"] = {
            "cfg": cfg,
            "msg": msg,
            "backend": backend,
            "kwargs": kwargs,
        }

    monkeypatch.setattr(client, "device_code", fake_device_code)
    monkeypatch.setattr("send.client.dispatch_send", fake_dispatch)

    msg = client.send(
        to=["dest@example.com"],
        subject="Hello",
        body_text="hi",
        interactive=False,
        scopes=["scope-a"],
        headers={"X-Test": "1"},
    )

    assert isinstance(msg, EmailMessage)
    assert msg["From"] == "ms-user@example.com"
    assert msg["To"] == "dest@example.com"
    assert msg["Subject"] == "Hello"
    assert msg["X-Test"] == "1"

    assert "device_code" in captured
    assert captured["device_code"]["interactive"] is False
    assert captured["device_code"]["scopes"] == ["scope-a"]

    dispatch = captured["dispatch"]
    assert dispatch["backend"] == "ms_graph"
    assert isinstance(dispatch["msg"], EmailMessage)
    assert dispatch["cfg"].get("backend") == "ms_graph"
    assert dispatch["cfg"].get("ms_email_address") == "ms-user@example.com"
    assert dispatch["kwargs"]["write_metadata"] is True
    assert dispatch["kwargs"]["access_token"] == "token-xyz"

    assert client.secure_config.saved  # config persisted


def test_send_dry_run_supports_custom_from(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path))

    client = EmailClient(
        backend="dry_run",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )
    client.secure_config = DummySecureConfig()

    called = {"device": 0, "dispatch": 0}

    def fake_device_code(**kwargs):
        called["device"] += 1
        return None

    def fake_dispatch(cfg, msg, backend, **kwargs):
        called["dispatch"] += 1
        called["cfg"] = cfg
        called["msg"] = msg
        called["backend"] = backend
        called["kwargs"] = kwargs

    monkeypatch.setattr(client, "device_code", fake_device_code)
    monkeypatch.setattr("send.client.dispatch_send", fake_dispatch)

    msg = client.send(
        from_address="custom@example.com",
        to="dest@example.com",
        subject="Dry run",
        body_text="preview",
        write_metadata=False,
    )

    assert called["device"] == 1
    assert called["dispatch"] == 1
    assert called["backend"] == "dry_run"
    assert msg["From"] == "custom@example.com"
    assert called["kwargs"]["write_metadata"] is False
    assert called["cfg"].get("backend") == "dry_run"


def test_send_dry_run_writes_eml_and_metadata(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path))
    monkeypatch.setattr(
        "send.runtime.paths.user_runtime_dir",
        lambda *args, **kwargs: str(runtime_dir),
    )

    client = EmailClient(
        backend="dry_run",
        key_policy={"prefer_keyring": False, "allow_passphrase_fallback": True},
        passphrase="pw",
    )
    client.secure_config = DummySecureConfig()

    with pytest.warns(RuntimeWarning):
        client.send(
            from_address="dryrun@example.com",
            to="dest@example.com",
            subject="Dry run output",
            body_text="preview",
        )

    out_dir = runtime_dir / "dry_run"
    eml_files = list(out_dir.glob("*.eml"))
    meta_files = list(out_dir.glob("*.json"))

    assert len(eml_files) == 1
    assert len(meta_files) == 1
    assert eml_files[0].stem == meta_files[0].stem
