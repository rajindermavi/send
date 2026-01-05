# auth/ 

## Purpose

The `auth/` package is responsible for **interactive token acquisition** for email-sending backends that require OAuth 2.0 access tokens.

This folder:

- Implements **device code flows** for providers that support them
- Acquires and caches **access tokens**
- Does **not** send email
- Does **not** construct messages
- Does **not** manage long-term credential storage directly

The output of this package is a **valid access token** that can be passed to a transport.

---

## Scope & Non-Goals

### In Scope

- Microsoft Graph device-code authentication
- Google API device-code authentication
- Token refresh via provider SDKs
- Optional UI callback for showing device-code instructions
- Loading/saving token caches via injected storage

### Explicitly Out of Scope

- Sending email
- Building email messages
- Managing encryption or key storage
- Handling “dry run” logic
- Acting as a general OAuth framework

---

## Files

auth/
├── __init__.py
├── auth.md
├── msal_device_code.py
└── google_api_device_code.py


---

## `msal_device_code.py`

### Responsibility

Acquire an **Microsoft Graph access token** using **MSAL Device Code Flow** for a *single mailbox*.

### Why Device Code Flow?

- Works for:
  - Personal Microsoft accounts
  - Small organizations
  - Unpaid / trial tenants
- Requires no local web server
- Works well for CLI and desktop tools
- Compatible with both `/consumers` and `/organizations`

---

### Primary Class

```python
class MSalDeviceCodeTokenProvider:
    """
    Handles access token acquisition for a single mailbox using
    MSAL Device Code Flow.
    """
```

### Public API

```
def acquire_token(self) -> str
```

This is the only required entry point.
- Starts device-code authentication if no valid token exists
- Refreshes token if expired
- Returns a raw access token string
- Raises on unrecoverable auth failure

**Expected Behavior**
- Uses msal.SerializableTokenCache
- Token cache loading/saving is injected (not hard-coded)
- Supports:
    - /common
    - /organizations
    - /consumers
- May optionally display the device-code message via callback

```
show_message: Callable[[object], None] | None
```

The auth layer **does not assume a UI.**

```google_api_device_code.py```

**Responsibility**

Acquire a Google API OAuth token using Device Authorization Grant.

This supports:

- Gmail API
- Google Workspace accounts
- CLI / headless workflows

**Primary Class**

```
class GoogleDeviceCodeTokenProvider:
    """
    Handles OAuth token acquisition for Google APIs
    using the device authorization flow.
    """
```

**Public API**

```def acquire_token(self) -> str```

- Initiates device-code authorization if needed
- Refreshes token when possible
- Returns a valid access token
- Raises on failure

---

**Notes**
- Uses Google OAuth client libraries
- Token persistence is injected
- Scope selection is explicit (e.g. gmail.send)
- No attempt is made to unify MS and Google auth flows

## Design Principles

- One provider = one file
- One provider = one public method
- No shared base classes unless duplication becomes painful
- Token acquisition is explicit, not magical
- Errors should fail fast and loudly

## Example Flow

1. Client code
2. auth.MSalDeviceCodeTokenProvider.acquire_token()
3. transport.GraphTransport(token)
4. transport.send_email(msg)

## Summary

- auth/ is small, explicit, and provider-specific
- Device-code flows are first-class
- Token acquisition has a single clear entry point