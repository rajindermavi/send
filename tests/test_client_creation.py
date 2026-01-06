from send.client import EmailClient


def test_email_client_initialization_with_configs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path))

    client = EmailClient(
        msal_config={
            "email_address": "ms-user@example.com",
            "client_id": "client-123",
            "smtp_port": "587",
            "smtp_starttls": "true",
        },
        google_api_config={
            "email_address": "gmail-user@example.com",
            "scopes": "https://mail.google.com/",
            "port": 443,
        },
        key_policy={
            "prefer_keyring": False,
            "allow_passphrase_fallback": True,
        },
        passphrase="test-passphrase",
    )

    assert client.msal_config is not None
    assert client.msal_config.smtp_port == 587
    assert client.msal_config.smtp_starttls is True

    assert client.google_api_config is not None
    assert client.google_api_config.port == 443
    assert client.google_api_config.scopes == ["https://mail.google.com/"]

    assert client.key_policy.prefer_keyring is False
    assert client.key_policy.allow_passphrase_fallback is True
    assert client.secure_config is not None
