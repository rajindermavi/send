# Nicemail

Nicemail is a small, explicit email-sending library for personal and small-team use.
It favors clarity and safety over abstraction.

## Quickstart
```python
from nicemail import EmailClient

client = EmailClient(backend="dry_run", out_dir="dry_run_out")
client.send(
    to="you@example.com",
    subject="Hello from Nicemail",
    body_text="This is a dry-run message.",
    from_address="me@example.com",
)
```

## CLI
```bash
nicemail dry-run --to you@example.com --from me@example.com --subject "Hello" --body "Test" --out-dir ./dry_run_out
nicemail send --backend ms_graph --to you@example.com --subject "Hello" --body "Hello from Nicemail" --email me@example.com --client-id YOUR_CLIENT_ID
```

