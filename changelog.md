# Changelog

## Unreleased
- Added Google device-code token provider with SecureConfig persistence and supporting tests.
- Implemented GoogleTransport for Gmail API sends; dispatcher now routes ms_graph, google_api, and dry_run backends.
- Renamed GraphMailClient to MSGraphTransport with backward-compatible send_message alias.
- Converted auth and message directories into importable modules; narrowed top-level exports to EmailClient only.
- Added coverage for Google transport behaviors and device-code flows.
- Introduced EmailMessageBuilder with attachment helpers and pytest coverage for message construction.
- Hardened SecureConfig to honor KeyPolicy and runtime paths, preferring keyring storage with optional passphrase-derived keys and no plaintext key file fallback.
- EmailClient now serializes/persists provider configs (MSAL/Google), key policy, and backend selection via SecureConfig, with dataclass-aware serialization helpers.
