import pytest

from send.message.builder import EmailMessageBuilder


def test_build_basic_text_email():
    msg = (
        EmailMessageBuilder()
        .set_from("sender@example.com")
        .add_to(["one@example.com", "Two <two@example.com>"])
        .set_subject("Hello")
        .set_text_body("hi there")
        .build()
    )

    assert msg["From"] == "sender@example.com"
    assert msg["To"] == "one@example.com, Two <two@example.com>"
    assert msg["Subject"] == "Hello"
    assert msg.get_content_type() == "text/plain"
    assert msg.get_content().strip() == "hi there"


def test_builds_alternative_when_html_and_text():
    msg = (
        EmailMessageBuilder()
        .set_from("sender@example.com")
        .add_to("recipient@example.com")
        .set_subject("Greetings")
        .set_text_body("Plain body")
        .set_html_body("<p>HTML body</p>")
        .build()
    )

    assert msg.is_multipart()
    plain = msg.get_body(preferencelist=("plain",))
    html = msg.get_body(preferencelist=("html",))

    assert plain is not None and plain.get_content_type() == "text/plain"
    assert html is not None and html.get_content_type() == "text/html"
    assert plain.get_content().strip() == "Plain body"
    assert html.get_content().strip() == "<p>HTML body</p>"


def test_adds_attachment_with_guessed_mime(tmp_path):
    file_path = tmp_path / "example.txt"
    file_path.write_text("example content", encoding="utf-8")

    msg = (
        EmailMessageBuilder()
        .set_from("sender@example.com")
        .add_to("recipient@example.com")
        .set_subject("Attachment test")
        .set_text_body("Body")
        .add_attachment(file_path)
        .build()
    )

    attachments = list(msg.iter_attachments())

    assert msg.is_multipart()
    assert len(attachments) == 1
    part = attachments[0]
    assert part.get_filename() == "example.txt"
    assert part.get_content_type() == "text/plain"
    assert part.get_payload(decode=True) == b"example content"


def test_missing_required_fields_raise():
    with pytest.raises(ValueError):
        EmailMessageBuilder().add_to("a@example.com").set_text_body("body").build()

    with pytest.raises(ValueError):
        EmailMessageBuilder().set_from("sender@example.com").set_text_body("body").build()

    with pytest.raises(ValueError):
        (
            EmailMessageBuilder()
            .set_from("sender@example.com")
            .add_to("a@example.com")
            .build()
        )
