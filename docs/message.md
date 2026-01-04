
# message/

The `message/` folder is responsible for **constructing fully-formed email messages**.

It does **not**:
- Send email
- Perform authentication
- Know anything about transport mechanisms (SMTP, Microsoft Graph, Google API, etc.)
- Store credentials or tokens

Its sole responsibility is to produce a valid `email.message.EmailMessage`
object that can be handed off to a transport for delivery.

---

## Design Goals

- Clean separation between **message construction** and **message delivery**
- One canonical way to build an `EmailMessage`
- Support common email features without leaking provider-specific details
- Remain small, explicit, and easy to reason about

This folder intentionally avoids abstractions that attempt to cover
every possible email use case.

---

## Public Contract

The output of this module is always:

email.message.EmailMessage


Transports assume the message is:
- Complete
- Valid
- Ready to send

No transport should modify message contents.

---

## Files

### `builder.py`

Contains the `EmailMessageBuilder` class.

This class provides a **structured, explicit API** for constructing
an `EmailMessage`, handling:

- From address
- To / CC / BCC
- Subject
- Plain text body
- HTML body (multipart/alternative)
- Attachments
- Headers (explicit, minimal)

The builder is responsible for ensuring the resulting message
conforms to RFC expectations for multipart emails.

---

## EmailMessageBuilder

### Responsibilities

- Normalize and validate address inputs
- Construct multipart messages when needed
- Attach files with correct MIME types
- Ensure headers are set consistently
- Produce a final `EmailMessage` instance

### Non-Responsibilities

- No retries
- No sending
- No logging of delivery success/failure
- No provider-specific logic
- No credential access

---

## Example Usage

```python
from message.builder import EmailMessageBuilder

msg = (
    EmailMessageBuilder()
        .set_from("reports@example.com")
        .add_to("client@example.com")
        .set_subject("Monthly Report")
        .set_text_body("Please find the report attached.")
        .add_attachment("report.pdf")
        .build()
)
```

The resulting msg can be passed directly to any transport:

transport.send_email(msg)

---

## Design Notes

- The builder pattern is used for clarity, not flexibility.
- Mutability is contained entirely within the builder.
- build() should be the only method that returns an EmailMessage.
- Validation errors should raise exceptions early.

---

## Future Extensions (Non-Goals for Now)

These may be added later if needed, but are intentionally excluded:

- Templating engines
- Jinja / HTML rendering
- Inline images
- Message persistence
- Draft storage

If these features are needed, they should live **above** this layer,
not inside it.

---

## Relationship to Other Modules

message/        → builds EmailMessage
transport/      → sends EmailMessage
credentials/    → manages secrets and tokens
client/         → orchestration and user-facing API

This strict layering keeps responsibilities clear and testable.


---

If you want, next good steps would be:
- Sketch `EmailMessageBuilder`’s **method surface** explicitly
- Decide whether attachments accept paths, bytes, or file-like objects
- Decide where address validation lives (builder vs helper)

But structurally, this `message.md` is exactly the right level of specificity.
