"""Agent core behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


class FakeEmailSender:
    """Capture outbound email payloads during tests."""

    def __init__(self) -> None:
        self.messages: list[dict[str, str | None]] = []

    async def send_email(self, *, to_email: str, subject: str, body: str, reply_to: str | None = None) -> str:
        """Record the outbound email and return a synthetic message id."""
        self.messages.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "reply_to": reply_to,
            }
        )
        return f"test-message-{len(self.messages)}"


@pytest_asyncio.fixture
async def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    """Create an isolated async database session."""
    from app.config import get_settings
    from app.database import dispose_database, get_session_maker, init_database, reset_database_state

    database_path = tmp_path / "agent-core.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.resolve().as_posix()}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_database_state()
    await init_database()

    async with get_session_maker()() as session:
        yield session

    await dispose_database()
    reset_database_state()
    get_settings.cache_clear()


async def create_default_thread(session: AsyncSession) -> str:
    """Create a default thread fixture for agent tests."""
    from app.agent.core import create_thread
    from app.schemas import ThreadConfig, ThreadCreate

    thread = await create_thread(
        session,
        ThreadCreate(
            prospect_email="prospect@example.com",
            prospect_name="Alex Prospect",
            config=ThreadConfig(
                gig_description="Three-week design sprint for a fintech landing page",
                budget_ceiling=5000,
                tone="warm, concise, and slightly casual",
                available_slots=[
                    "2026-05-05T10:00:00+05:30",
                    "2026-05-05T14:00:00+05:30",
                    "2026-05-06T11:00:00+05:30",
                ],
            ),
        ),
    )
    return thread.id


@pytest.mark.asyncio
async def test_agent_turn_sends_initial_outreach(db_session: AsyncSession) -> None:
    """Initial turns should send one outbound email and mark outreach sent."""
    from app.agent.core import get_thread_detail, run_agent_turn

    thread_id = await create_default_thread(db_session)
    sender = FakeEmailSender()

    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Quick contract role",
                "body": "Saw your portfolio and thought you'd be a strong fit for a short sprint. Open to a quick call this week?",
            }
        ),
        email_sender=sender,
    )

    thread = await get_thread_detail(db_session, thread_id)

    assert thread.status == "outreach_sent"
    assert len(thread.messages) == 1
    assert thread.messages[0].direction == "outbound"
    assert len(sender.messages) == 1


@pytest.mark.asyncio
async def test_agent_turn_negotiates_after_budget_pushback(db_session: AsyncSession) -> None:
    """Negotiation replies should keep the thread active and send one answer."""
    from app.agent.core import add_inbound_message, get_thread_detail, run_agent_turn

    thread_id = await create_default_thread(db_session)
    sender = FakeEmailSender()
    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Quick contract role",
                "body": "Open to a quick intro call later this week?",
            }
        ),
        email_sender=sender,
    )
    await add_inbound_message(
        db_session,
        thread_id=thread_id,
        subject="Re: Quick contract role",
        body="I'd be interested, but I usually need at least $4,800 for a sprint like this.",
    )

    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Re: Quick contract role",
                "body": "We can get close to that range for the right fit. If you're open, I'd love to outline the scope and see if it feels aligned.",
            }
        ),
        email_sender=sender,
    )

    thread = await get_thread_detail(db_session, thread_id)

    assert thread.status == "negotiating"
    assert len(thread.messages) == 3
    assert len(sender.messages) == 2


@pytest.mark.asyncio
async def test_agent_turn_proposes_slots_and_confirms_booking(db_session: AsyncSession) -> None:
    """A proposed slot followed by acceptance should create a booking."""
    from app.agent.core import add_inbound_message, get_thread_detail, run_agent_turn

    thread_id = await create_default_thread(db_session)
    sender = FakeEmailSender()
    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Quick contract role",
                "body": "Would you be open to a quick intro call this week?",
            }
        ),
        email_sender=sender,
    )
    await add_inbound_message(
        db_session,
        thread_id=thread_id,
        subject="Re: Quick contract role",
        body="This is interesting. Happy to find a time.",
    )
    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "propose_calendar_slot",
                "body": "Great. I can do Tuesday 10:00, Tuesday 14:00, or Wednesday 11:00 if one of those works for you.",
                "slots": [
                    "2026-05-05T10:00:00+05:30",
                    "2026-05-05T14:00:00+05:30",
                    "2026-05-06T11:00:00+05:30",
                ],
            }
        ),
        email_sender=sender,
    )
    await add_inbound_message(
        db_session,
        thread_id=thread_id,
        subject="Re: Quick contract role",
        body="Tuesday 10:00 works for me.",
    )

    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Re: Quick contract role",
                "body": "Perfect. I've locked that in and sent over the calendar hold.",
            }
        ),
        email_sender=sender,
    )

    thread = await get_thread_detail(db_session, thread_id)

    assert thread.status == "booked"
    assert len(thread.bookings) == 1
    assert thread.bookings[0].status == "confirmed"
    assert thread.bookings[0].slot == "2026-05-05T10:00:00+05:30"


@pytest.mark.asyncio
async def test_agent_turn_walks_away_when_budget_is_out_of_range(db_session: AsyncSession) -> None:
    """An explicit mismatch should close the thread with a polite final note."""
    from app.agent.core import add_inbound_message, get_thread_detail, run_agent_turn

    thread_id = await create_default_thread(db_session)
    sender = FakeEmailSender()
    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Quick contract role",
                "body": "Would love to share details if you're open to it.",
            }
        ),
        email_sender=sender,
    )
    await add_inbound_message(
        db_session,
        thread_id=thread_id,
        subject="Re: Quick contract role",
        body="Thanks, but I couldn't take this for less than $8,500.",
    )

    await run_agent_turn(
        db_session,
        thread_id=thread_id,
        llm_response_override=json.dumps(
            {
                "name": "walk_away",
                "body": "Appreciate the clarity. I don't want to waste your time if the budget isn't a fit, but I'd be glad to keep you in mind for future roles.",
            }
        ),
        email_sender=sender,
    )

    thread = await get_thread_detail(db_session, thread_id)

    assert thread.status == "closed_no_fit"
    assert thread.messages[-1].direction == "outbound"
