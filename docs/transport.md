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
- Use cached authentication tokens
- Raise exceptions on failure

## Contract

All transports expose:

    send_email(msg: EmailMessage) -> None

The message is assumed to be complete and valid.

The transport must not mutate the EmailMessage.

Transports are designed for one-shot message delivery.
They may internally reuse cached tokens or HTTP clients.
Callers should assume each send_email call is independent.

## dry_run_transport.py

A no-op transport used for testing, debugging, and previewing sends.

- Implements the same contract as all transports
- Performs no network calls
- Does not mutate the EmailMessage
- Logs or records send intent only

## ms_graph_transport.py

- Sends email via Microsoft Graph
- Uses cached MSAL tokens
- Sends a single EmailMessage
- Does not retry on failure

## google_transport.py

- Sends email via Google API
- Uses cached OAuth tokens
- Sends a single EmailMessage
- Does not retry on failure

## send.py

Provides a thin dispatch layer over available transports.

send(cfg: dict, msg: EmailMessage, backend: Backend) -> None

- Selects the appropriate transport based on backend
- Constructs the transport using cfg
- Delegates to transport.send_email
- Does not implement retries, logging policy, or validation

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