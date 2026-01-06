import base64
from email import message_from_bytes
from email.message import EmailMessage

import pytest

from send.transport.google_transport import GoogleTransport


class DummyResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(payload)

    def json(self):
        return self._payload


def test_google_transport_sets_from_on_copy(monkeypatch):
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyResponse(200, {})

    monkeypatch.setattr("send.transport.google_transport.requests.post", fake_post)

    msg = EmailMessage()
    msg["To"] = "dest@example.com"
    msg.set_content("hello")

    transport = GoogleTransport("token-123", "sender@example.com")
    transport.send_email(msg)

    assert "From" not in msg  # original untouched

    raw = captured["json"]["raw"]
    decoded = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert decoded["From"] == "sender@example.com"
    assert captured["headers"]["Authorization"] == "Bearer token-123"


def test_google_transport_raises_on_http_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResponse(400, {"error": "bad"})

    monkeypatch.setattr("send.transport.google_transport.requests.post", fake_post)

    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "dest@example.com"
    msg.set_content("hi")

    transport = GoogleTransport("token-123", "sender@example.com")

    with pytest.raises(RuntimeError):
        transport.send_email(msg)


def test_connect_with_oauth_uses_provider_and_config(monkeypatch):
    class FakeProvider:
        def __init__(self) -> None:
            self.interactive = None
            self.scopes = None

        def acquire_token(self, interactive=True, scopes=None):
            self.interactive = interactive
            self.scopes = scopes
            return "token-xyz"

    cfg = {
        "google_email_address": "user@example.com",
        "google_client_id": "client-1",
        "google_api_config": {
            "host": "example.googleapis.com",
            "scopes": ["scope-a", "scope-b"],
        },
    }

    provider = FakeProvider()
    transport = GoogleTransport.connect_with_oauth(cfg, token_provider=provider, interactive=False)

    assert provider.interactive is False
    assert provider.scopes == ["scope-a", "scope-b"]
    assert isinstance(transport, GoogleTransport)
    assert transport._host == "example.googleapis.com"
