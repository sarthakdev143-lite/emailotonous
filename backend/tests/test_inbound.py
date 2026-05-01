"""Inbound IMAP polling tests."""

from __future__ import annotations

from email.message import EmailMessage

import pytest


def build_email(
    *,
    from_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
) -> EmailMessage:
    """Build a simple email message for tests."""
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = "agent@example.com"
    message["Subject"] = subject
    message["Message-ID"] = "<message@example.com>"
    if in_reply_to is not None:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)
    return message


def test_match_thread_prefers_in_reply_to_header() -> None:
    """Use RFC message threading headers before fallback heuristics."""
    from app.email.inbound import IMAPPoller, ThreadCandidate

    poller = IMAPPoller(session_factory=lambda: None)
    email_message = build_email(
        from_email="prospect@example.com",
        subject="Re: Launch sprint role",
        body="Could we move this?",
        in_reply_to="<thread-message-1@example.com>",
    )

    result = poller.match_thread(
        email_message,
        [
            ThreadCandidate(
                thread_id="thread-1",
                prospect_email="prospect@example.com",
                subject="Launch sprint role",
                status="booked",
                message_ids=["<thread-message-1@example.com>"],
            )
        ],
    )

    assert result == "thread-1"


def test_match_thread_falls_back_to_subject_normalization() -> None:
    """Normalize reply prefixes when matching by subject."""
    from app.email.inbound import IMAPPoller, ThreadCandidate

    poller = IMAPPoller(session_factory=lambda: None)
    email_message = build_email(
        from_email="prospect@example.com",
        subject="Re: Launch sprint role",
        body="Still interested.",
    )

    result = poller.match_thread(
        email_message,
        [
            ThreadCandidate(
                thread_id="thread-2",
                prospect_email="someone@example.com",
                subject="Launch sprint role",
                status="outreach_sent",
                message_ids=[],
            )
        ],
    )

    assert result == "thread-2"


def test_match_thread_uses_sender_as_last_resort() -> None:
    """Fall back to sender matching when headers and subject are missing."""
    from app.email.inbound import IMAPPoller, ThreadCandidate

    poller = IMAPPoller(session_factory=lambda: None)
    email_message = build_email(
        from_email="prospect@example.com",
        subject="Checking in",
        body="Wanted to circle back.",
    )

    result = poller.match_thread(
        email_message,
        [
            ThreadCandidate(
                thread_id="thread-3",
                prospect_email="prospect@example.com",
                subject="Different subject",
                status="negotiating",
                message_ids=[],
            )
        ],
    )

    assert result == "thread-3"


@pytest.mark.asyncio
async def test_process_new_email_saves_inbound_message_and_triggers_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persist the inbound email and trigger an agent turn."""
    from app.email.inbound import IMAPPoller

    captured: dict[str, object] = {}

    class DummySessionContext:
        """Yield a placeholder async session object."""

        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    async def fake_add_inbound_message(
        session: object,
        *,
        thread_id: str,
        subject: str | None,
        body: str,
        email_message_id: str | None = None,
    ) -> None:
        captured["thread_id"] = thread_id
        captured["subject"] = subject
        captured["body"] = body
        captured["email_message_id"] = email_message_id

    async def fake_run_agent_turn(session: object, *, thread_id: str) -> None:
        captured["triggered_thread_id"] = thread_id

    monkeypatch.setattr("app.email.inbound.add_inbound_message", fake_add_inbound_message)
    monkeypatch.setattr("app.email.inbound.run_agent_turn", fake_run_agent_turn)

    poller = IMAPPoller(session_factory=DummySessionContext)
    email_message = build_email(
        from_email="prospect@example.com",
        subject="Re: Launch sprint role",
        body="Could we move this to tomorrow?",
        in_reply_to="<thread-message-1@example.com>",
    )

    await poller.process_new_email(email_message.as_bytes(), "thread-4")

    assert captured["thread_id"] == "thread-4"
    assert captured["subject"] == "Re: Launch sprint role"
    assert captured["body"] == "Could we move this to tomorrow?\n"
    assert captured["email_message_id"] == "<message@example.com>"
    assert captured["triggered_thread_id"] == "thread-4"
