# transport/

transport/ is responsible for delivering fully-constructed email messages
via provider-specific APIs (Microsoft Graph, Google).

It does not construct email content or manage credentials directly.

## Responsibilities

- Send a single EmailMessage
- Support:
  - To / CC / BCC
  - Subject
  - Body (plain or multipart)
  - Attachments
- Use caller-provided authentication tokens
- Raise exceptions on failure

## Contract

All transports expose:

    send_email(msg: EmailMessage) -> None

The message is assumed to be complete and valid.

The transport must not mutate the EmailMessage.

Transports are designed for one-shot message delivery.
They may internally reuse HTTP clients.
Callers should assume each send_email call is independent.
Transports do not acquire tokens; callers supply them explicitly.

## dry_run_transport.py

A no-op transport used for testing, debugging, and previewing sends.

- Implements the same contract as all transports
- Performs no network calls
- Does not mutate the EmailMessage
- Logs or records send intent only
- EmailClient defaults output to platformdirs.user_runtime_dir("send") / "dry_run"

## ms_graph_transport.py

- Sends email via Microsoft Graph
- Uses caller-provided access tokens
- Sends a single EmailMessage
- Does not retry on failure

## google_transport.py

- Sends email via Google API
- Uses caller-provided access tokens
- Sends a single EmailMessage
- Does not retry on failure

## send.py

Provides a thin dispatch layer over available transports.

send(cfg: dict, msg: EmailMessage, backend: Backend, *, out_dir: Path | None = None, access_token: str | None = None) -> None

- Selects the appropriate transport based on backend
- Constructs the transport using cfg
- Delegates to transport.send_email
- Does not implement retries, logging policy, or validation
- For dry_run, out_dir is required and must be supplied by the caller
- For provider backends, access_token is required and must be supplied by the caller

EmailClient.send() wraps this dispatcher: it builds the EmailMessage via
EmailMessageBuilder, persists config using the configured KeyPolicy/SecureConfig,
runs device-code auth for non-dry-run backends, and then calls this send() helper
with the acquired access token.

## Errors

send_email raises a TransportError (or subclass) if delivery fails.
Provider-specific exceptions may be wrapped.
Transports do not retry internally.

## Limitations

- Large attachments may fail depending on provider limits.
- Attachment size limits are enforced by providers, not this library.
- Chunked uploads are not currently supported.
- Inline images are treated as regular attachments.

## Non-Goals

- Email composition
- Full email client functionality (folders, threading, search)
- Provider-agnostic feature parity
- Multi-account orchestration
- Long-lived sessions or retries
