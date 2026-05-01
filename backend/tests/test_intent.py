"""Intent classification tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message_body", "history", "expected"),
    [
        (None, [], "initial"),
        ("This looks interesting. I'd love to learn more.", [], "interested"),
        ("Can you share a little more about the scope and team?", [], "curious"),
        ("I'd need at least $8,000 to make this worth my time.", [], "negotiating"),
        ("Need to cancel tomorrow's call. Can we reschedule for next week?", [], "cancellation"),
        ("Thanks for reaching out, but I have to pass on this one.", [], "declining"),
        (None, ["Previous outreach message"], "silent"),
    ],
)
async def test_classify_intent_returns_expected_label(
    message_body: str | None,
    history: list[str],
    expected: str,
) -> None:
    """Classify common recruiter thread intents."""
    from app.agent.intent import classify_intent

    result = await classify_intent(message_body=message_body, history=history)

    assert result.value == expected
