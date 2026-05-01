"""Reschedule loop integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


class FakeEmailSender:
    """Capture outbound messages during loop tests."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send_email(
        self, *, to_email: str, subject: str, body: str, reply_to: str | None = None
    ) -> str:
        """Record the email body and return a synthetic id."""
        self.messages.append(body)
        return f"loop-message-{len(self.messages)}"


@pytest_asyncio.fixture
async def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    """Create an isolated database for the reschedule loop."""
    from app.config import get_settings
    from app.database import (
        dispose_database,
        get_session_maker,
        init_database,
        reset_database_state,
    )

    database_path = tmp_path / "reschedule-loop.db"
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


def build_slots(iteration: int) -> list[str]:
    """Generate deterministic replacement slots for each cycle."""
    base_day = 8 + iteration
    return [
        f"2026-05-{base_day:02d}T10:00:00+05:30",
        f"2026-05-{base_day:02d}T14:00:00+05:30",
        f"2026-05-{base_day + 1:02d}T11:00:00+05:30",
    ]


@pytest.mark.asyncio
async def test_reschedule_loop_handles_five_cancellations_without_losing_context(
    db_session: AsyncSession,
) -> None:
    """Repeated cancellations should preserve thread coherence across five loops."""
    from app.agent.core import add_inbound_message, create_thread, get_thread_detail, run_agent_turn
    from app.schemas import ThreadConfig, ThreadCreate

    sender = FakeEmailSender()
    thread = await create_thread(
        db_session,
        ThreadCreate(
            prospect_email="prospect@example.com",
            prospect_name="Casey Calendar",
            config=ThreadConfig(
                gig_description="Six-week product launch sprint",
                budget_ceiling=6000,
                tone="warm and direct",
                available_slots=build_slots(iteration=0),
            ),
        ),
    )

    await run_agent_turn(
        db_session,
        thread_id=thread.id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Launch sprint role",
                "body": "Would you be up for a quick intro call this week?",
            }
        ),
        email_sender=sender,
    )
    await add_inbound_message(
        db_session,
        thread_id=thread.id,
        subject="Re: Launch sprint role",
        body="Sounds good. Happy to grab time.",
    )
    await run_agent_turn(
        db_session,
        thread_id=thread.id,
        llm_response_override=json.dumps(
            {
                "name": "propose_calendar_slot",
                "body": "Great. Here are three times that work on my side.",
                "slots": build_slots(iteration=0),
            }
        ),
        email_sender=sender,
    )
    await add_inbound_message(
        db_session,
        thread_id=thread.id,
        subject="Re: Launch sprint role",
        body="The first slot works for me.",
    )
    await run_agent_turn(
        db_session,
        thread_id=thread.id,
        llm_response_override=json.dumps(
            {
                "name": "send_email",
                "subject": "Re: Launch sprint role",
                "body": "Perfect. I've got it on the calendar.",
            }
        ),
        email_sender=sender,
    )

    for iteration in range(1, 6):
        current_thread = await get_thread_detail(db_session, thread.id)
        current_slot = current_thread.bookings[-1].slot
        new_slots = build_slots(iteration=iteration)

        await add_inbound_message(
            db_session,
            thread_id=thread.id,
            subject="Re: Launch sprint role",
            body=f"I need to reschedule the {current_slot} hold. Could we move it?",
        )
        await run_agent_turn(
            db_session,
            thread_id=thread.id,
            llm_response_override=json.dumps(
                {
                    "name": "reschedule",
                    "body": "Absolutely. Here are a few updated options.",
                    "cancelled_slot": current_slot,
                    "new_slots": new_slots,
                }
            ),
            email_sender=sender,
        )
        await add_inbound_message(
            db_session,
            thread_id=thread.id,
            subject="Re: Launch sprint role",
            body="The first updated slot works for me.",
        )
        await run_agent_turn(
            db_session,
            thread_id=thread.id,
            llm_response_override=json.dumps(
                {
                    "name": "send_email",
                    "subject": "Re: Launch sprint role",
                    "body": "Locked in. I'll see you then.",
                }
            ),
            email_sender=sender,
        )

    final_thread = await get_thread_detail(db_session, thread.id)
    booking_statuses = [booking.status for booking in final_thread.bookings]

    assert final_thread.status == "booked"
    assert len(final_thread.bookings) == 6
    assert booking_statuses.count("confirmed") == 1
    assert booking_statuses.count("rescheduled") == 5
    assert final_thread.bookings[-1].slot == build_slots(iteration=5)[0]
    assert len(final_thread.messages) == 5 + (5 * 4)
