
# credentials/

This library intentionally favors simplicity and locality over maximal abstraction.

The credentials subsystem is designed for single-user or small-organization workflows, where the same runtime both configures and uses credentials. Models may therefore combine static configuration, cached runtime state, and token metadata in one place to reduce cognitive and persistence overhead.

This is not intended to be a general-purpose secret-management framework.


## Design Principles

- Prefer explicitness over indirection
- Prefer local encrypted storage over remote secret services
- Avoid premature abstraction (no provider registries, no layered adapters)
- Make the security boundary obvious
- Fail safely rather than silently weakening security
- Support headless / CLI / device-code flows
- Library-first: no global singletons, no hidden side effects

---

## Folder Overview

credentials/
├── paths.py
├── models.py
└── store.py



---

## Supported Credential Storage Modes

Exactly **two** storage modes are supported.

### 1. Encrypted File + System Keyring Key (Preferred)

- Credential data is encrypted and written to disk
- A randomly generated encryption key is stored in the OS keyring
- The encrypted file contains **no usable secret material on its own**

This is the **default and recommended** configuration.

---

### 2. Encrypted File + User-Supplied Key

- Credential data is encrypted and written to disk
- The encryption key is supplied by the user at runtime
- **No encryption key is stored** (not on disk, not in keyring)

This mode is intended for:
- Headless systems
- Restricted environments
- Users who explicitly do not want keyring usage

---

### Explicit Non-Goals

The following are **not supported**:

- Plaintext credential storage
- Encrypted file + key stored in a file
- Automatic downgrade from keyring to file-based keys
- Backup key files
- Mixed or hybrid key storage schemes

If neither of the two supported modes is possible, the operation **fails**.

---

## `paths.py`

Defines **where encrypted credential data is stored**.

### Responsibilities

- Provide platform-appropriate storage locations
- Centralize all filesystem paths used by the credentials system
- Avoid OS-specific logic elsewhere in the codebase

### Notes

- Paths are user-scoped
- Derived using `platformdirs`
- No directories are created implicitly

---

## `models.py`

Defines **plain data models** used by the credentials subsystem.

### Design Intent

- Models are dataclasses
- Models may contain:
  - Static configuration
  - Cached runtime state (e.g. tokens, timestamps)
- Models do **not**:
  - Perform I/O
  - Encrypt data
  - Access keyrings

---

### `MSalConfig`

Represents configuration and cached state for Microsoft Graph email access.

Typical contents:

- Username and email address
- Client ID
- Authority (`organization` or `consumer`)
- Cached access token (optional)
- Token timestamp (optional)

A single instance fully describes a mailbox and its current authentication state.

---

### `GoogleAPIConfig`

Represents configuration and cached state for Google email access.

Typical contents:

- Email address
- Client ID
- OAuth scopes
- Cached access token (optional)
- Token timestamp (optional)

As with `MSalConfig`, runtime state is stored alongside static configuration.

---

### `KeyPolicy`

Defines **which of the two supported key strategies is allowed**.

Typical fields:

- `prefer_keyring: bool`
- `allow_user_key: bool`

`KeyPolicy` is declarative only.  
It does **not** store keys or perform encryption.

---

## `store.py`

Contains the **only persistence and encryption logic** in the system.

### `SecureConfig`

`SecureConfig` is responsible for:

- Serializing credential models
- Encrypting serialized data
- Writing encrypted data to disk
- Retrieving encryption keys from:
  - System keyring **or**
  - User-supplied passphrase
- Decrypting and restoring models

---

## Key Handling Rules

### Keyring Mode

If:

- `prefer_keyring == True`
- A system keyring is available and writable

Then:

- A random encryption key is generated
- The key is stored in the OS keyring
- The encrypted config file is written to disk

---

### User-Supplied Key Mode

If:

- `prefer_keyring == False` **or** keyring access fails
- `allow_user_key == True`

Then:

- The user must provide a key or passphrase at runtime
- A cryptographic key is derived in memory
- The encrypted config file is written to disk
- **No key material is persisted**

---

### Failure Conditions

If:

- Keyring usage is disallowed or unavailable **and**
- User-supplied keys are disallowed

Then:

- `SecureConfig` raises an explicit error
- No data is written

There is **no silent fallback**.

---

## Security Notes

- The encrypted file may be readable by the user
- Security relies on:
  - OS account isolation
  - Keyring protections **or** passphrase secrecy
- This protects against:
  - Accidental disclosure
  - Casual inspection
- This does **not** protect against:
  - A fully compromised user account

This threat model is intentional and appropriate for the scope.

---

## Typical Usage Flow

1. Create a credential model (`MSalConfig` or `GoogleAPIConfig`)
2. Define a `KeyPolicy`
3. Initialize `SecureConfig`
4. Encrypt and save credentials
5. Later:
   - Load and decrypt credentials
   - Reuse cached tokens or refresh as needed

---

## Rationale

This design prioritizes:

- Predictability
- Auditability
- Ease of reasoning
- Minimal moving parts

It avoids enterprise-grade complexity while still enforcing **clear security boundaries**.
