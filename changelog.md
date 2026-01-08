# Changelog

## Unreleased
- EmailClient.send now builds messages, persists config, runs device-code auth, and dispatches via transports.
- Added EmailClient.message() helper that builds EmailMessage instances via EmailMessageBuilder with sensible defaults.
- Added EmailClient.device_code() to trigger provider-specific device flows and warn when using the dry_run backend.
- Dry-run sends now default to platformdirs.user_runtime_dir("send")/dry_run via EmailClient, with explicit out_dir required by the dispatcher.
- SecureConfig now enables passphrase fallback when keyring is unavailable, with a one-time warning.
- EmailClient now acquires access tokens once per send and transports consume the provided token without re-authenticating.
- Added Google device-code token provider with SecureConfig persistence and supporting tests.
- Implemented GoogleTransport for Gmail API sends; dispatcher now routes ms_graph, google_api, and dry_run backends.
- Renamed GraphMailClient to MSGraphTransport with backward-compatible send_message alias.
- Converted auth and message directories into importable modules; narrowed top-level exports to EmailClient only.
- Added coverage for Google transport behaviors and device-code flows.
- Introduced EmailMessageBuilder with attachment helpers and pytest coverage for message construction.
- Hardened SecureConfig to honor KeyPolicy and runtime paths, preferring keyring storage with optional passphrase-derived keys and no plaintext key file fallback.
- EmailClient now serializes/persists provider configs (MSAL/Google), key policy, and backend selection via SecureConfig, with dataclass-aware serialization helpers.
