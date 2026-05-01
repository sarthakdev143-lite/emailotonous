"""Main agent orchestration loop and thread persistence helpers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.intent import Intent, classify_intent
from app.agent.prompts import build_system_prompt
from app.agent.tools import (
    ProposeCalendarSlotAction,
    RescheduleAction,
    SendEmailAction,
    WalkAwayAction,
    parse_tool_call,
)
from app.calendar.stub import CalendarStub
from app.config import (
    BOOKING_STATUS_RESCHEDULED,
    DEFAULT_REPLY_SUBJECT,
    MESSAGE_DIRECTION_INBOUND,
    MESSAGE_DIRECTION_OUTBOUND,
    THREAD_STATUS_BOOKED,
    THREAD_STATUS_CLOSED_NO_FIT,
    THREAD_STATUS_NEGOTIATING,
    THREAD_STATUS_OUTREACH_SENT,
    THREAD_STATUS_PENDING,
    THREAD_STATUS_SLOT_PROPOSED,
    get_settings,
)
from app.email.outbound import ResendEmailSender, SupportsEmailSending
from app.llm_client import complete
from app.models import Booking, Message, Thread
from app.schemas import BookingRead, MessageRead, ThreadConfig, ThreadCreate, ThreadDetail, ThreadSummary

LOGGER = logging.getLogger(__name__)


async def create_thread(session: AsyncSession, payload: ThreadCreate) -> Thread:
    """Create and persist a new prospect thread."""
    thread = Thread(
        id=str(uuid4()),
        prospect_email=str(payload.prospect_email),
        prospect_name=payload.prospect_name,
        status=THREAD_STATUS_PENDING,
        config=payload.config.model_dump(),
    )
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return thread


async def add_inbound_message(
    session: AsyncSession,
    *,
    thread_id: str,
    subject: str | None,
    body: str,
    email_message_id: str | None = None,
) -> Message:
    """Store an inbound message and classify its intent."""
    history = await _message_bodies_for_thread(session, thread_id)
    intent = await classify_intent(message_body=body, history=history)
    message = Message(
        id=str(uuid4()),
        thread_id=thread_id,
        direction=MESSAGE_DIRECTION_INBOUND,
        subject=subject,
        body=body,
        email_message_id=email_message_id,
        intent=intent.value,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_thread_detail(session: AsyncSession, thread_id: str) -> ThreadDetail:
    """Return a fully populated thread detail payload."""
    thread = await _get_thread(session, thread_id)
    return _serialize_thread(thread)


async def list_threads(session: AsyncSession) -> list[ThreadSummary]:
    """Return thread summaries for the dashboard list."""
    result = await session.execute(
        select(Thread)
        .options(selectinload(Thread.messages), selectinload(Thread.bookings))
        .order_by(Thread.updated_at.desc())
    )
    return [_serialize_thread_summary(thread) for thread in result.scalars().all()]


async def run_agent_turn(
    session: AsyncSession,
    *,
    thread_id: str,
    llm_response_override: str | None = None,
    email_sender: SupportsEmailSending | None = None,
    calendar_service: CalendarStub | None = None,
) -> ThreadDetail:
    """Execute one perceive, reason, act cycle for a thread."""
    thread = await _get_thread(session, thread_id)
    latest_inbound = _latest_inbound_message(thread.messages)
    history_bodies = [message.body for message in thread.messages[:-1]] if latest_inbound else [message.body for message in thread.messages]
    intent = Intent.INITIAL if latest_inbound is None else await classify_intent(latest_inbound.body, history_bodies)

    if llm_response_override is None:
        llm_response_override = await _complete_agent_turn(thread)

    action = parse_tool_call(llm_response_override)
    sender = email_sender or ResendEmailSender()
    calendar = calendar_service or CalendarStub(session)

    await _execute_action(
        session=session,
        thread=thread,
        latest_inbound=latest_inbound,
        intent=intent,
        action=action,
        email_sender=sender,
        calendar_service=calendar,
    )
    await session.commit()
    return await get_thread_detail(session, thread_id)


async def _complete_agent_turn(thread: Thread) -> str:
    """Request a tool call from the configured server-side LLM."""
    history_entries = [message.body for message in thread.messages]
    conversation = [
        {
            "role": "assistant" if message.direction == MESSAGE_DIRECTION_OUTBOUND else "user",
            "content": message.body,
        }
        for message in thread.messages
    ]
    return await complete(
        messages=conversation,
        system=build_system_prompt(thread.config, history_entries, get_settings().company_name),
    )


async def _execute_action(
    *,
    session: AsyncSession,
    thread: Thread,
    latest_inbound: Message | None,
    intent: Intent,
    action: SendEmailAction | ProposeCalendarSlotAction | WalkAwayAction | RescheduleAction,
    email_sender: SupportsEmailSending,
    calendar_service: CalendarStub,
) -> None:
    """Execute the selected action and persist side effects."""
    subject = _derive_subject(thread.messages, action)
    reply_to = latest_inbound.email_message_id if latest_inbound is not None else None

    if isinstance(action, ProposeCalendarSlotAction):
        thread.config = {**thread.config, "available_slots": action.slots}
        await _send_outbound_message(session, thread, subject, action.body, reply_to, email_sender)
        thread.status = THREAD_STATUS_SLOT_PROPOSED
    elif isinstance(action, RescheduleAction):
        await _mark_latest_booking_rescheduled(session, thread.id, action.cancelled_slot)
        thread.config = {**thread.config, "available_slots": action.new_slots}
        await _send_outbound_message(session, thread, subject, action.body, reply_to, email_sender)
        thread.status = THREAD_STATUS_SLOT_PROPOSED
    elif isinstance(action, WalkAwayAction):
        await _send_outbound_message(session, thread, subject, action.body, reply_to, email_sender)
        thread.status = THREAD_STATUS_CLOSED_NO_FIT
    else:
        await _send_outbound_message(session, thread, action.subject, action.body, reply_to, email_sender)
        if _should_confirm_booking(thread.status, latest_inbound):
            slot = _pick_booking_slot(thread.config.get("available_slots", []), latest_inbound.body if latest_inbound else "")
            await calendar_service.book_slot(thread.id, slot)
            thread.status = THREAD_STATUS_BOOKED
        elif thread.status == THREAD_STATUS_PENDING:
            thread.status = THREAD_STATUS_OUTREACH_SENT
        elif intent == Intent.NEGOTIATING or thread.status == THREAD_STATUS_NEGOTIATING:
            thread.status = THREAD_STATUS_NEGOTIATING
        else:
            thread.status = THREAD_STATUS_NEGOTIATING

    thread.updated_at = datetime.now().astimezone()
    session.add(thread)
    await session.flush()


async def _send_outbound_message(
    session: AsyncSession,
    thread: Thread,
    subject: str,
    body: str,
    reply_to: str | None,
    email_sender: SupportsEmailSending,
) -> None:
    """Send and persist a single outbound message."""
    message_id = await email_sender.send_email(
        to_email=thread.prospect_email,
        subject=subject,
        body=body,
        reply_to=reply_to,
    )
    message = Message(
        id=str(uuid4()),
        thread_id=thread.id,
        direction=MESSAGE_DIRECTION_OUTBOUND,
        subject=subject,
        body=body,
        email_message_id=message_id,
        intent=None,
    )
    session.add(message)
    await session.flush()


def _derive_subject(messages: list[Message], action: Any) -> str:
    """Determine the subject line for an outbound reply."""
    if hasattr(action, "subject"):
        return str(action.subject)
    for message in reversed(messages):
        if message.subject:
            return message.subject
    return DEFAULT_REPLY_SUBJECT


def _should_confirm_booking(current_status: str, latest_inbound: Message | None) -> bool:
    """Return whether the latest inbound message confirms a proposed slot."""
    if current_status != THREAD_STATUS_SLOT_PROPOSED or latest_inbound is None:
        return False
    normalized = latest_inbound.body.lower()
    return any(token in normalized for token in ("works", "confirmed", "book it", "sounds good", "let's do"))


def _pick_booking_slot(slots: list[Any], latest_body: str) -> str:
    """Choose the best-matching slot from the latest proposal."""
    normalized_body = latest_body.lower()
    for slot_value in slots:
        slot = str(slot_value)
        try:
            slot_time = datetime.fromisoformat(slot)
        except ValueError:
            continue
        weekday = slot_time.strftime("%A").lower()
        hour = slot_time.strftime("%H:%M").lower()
        hour_short = str(int(slot_time.strftime("%H")))
        if weekday in normalized_body and (hour in normalized_body or hour_short in normalized_body):
            return slot
    if not slots:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No available slots to book.")
    return str(slots[0])


async def _mark_latest_booking_rescheduled(session: AsyncSession, thread_id: str, cancelled_slot: str) -> None:
    """Mark the matching booking as rescheduled."""
    result = await session.execute(
        select(Booking)
        .where(Booking.thread_id == thread_id)
        .where(Booking.slot == cancelled_slot)
        .order_by(Booking.created_at.desc())
    )
    booking = result.scalars().first()
    if booking is not None:
        booking.status = BOOKING_STATUS_RESCHEDULED
        await session.flush()


async def _get_thread(session: AsyncSession, thread_id: str) -> Thread:
    """Load a thread or raise a 404 error."""
    result = await session.execute(
        select(Thread)
        .where(Thread.id == thread_id)
        .options(selectinload(Thread.messages), selectinload(Thread.bookings))
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found.")
    return thread


async def _message_bodies_for_thread(session: AsyncSession, thread_id: str) -> list[str]:
    """Return message bodies for a thread ordered by timestamp."""
    result = await session.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.timestamp.asc())
    )
    return [message.body for message in result.scalars().all()]


def _latest_inbound_message(messages: list[Message]) -> Message | None:
    """Return the latest inbound message in a thread."""
    inbound_messages = [message for message in messages if message.direction == MESSAGE_DIRECTION_INBOUND]
    return inbound_messages[-1] if inbound_messages else None


def _serialize_thread(thread: Thread) -> ThreadDetail:
    """Serialize an ORM thread into a detailed schema payload."""
    return ThreadDetail(
        **_serialize_thread_summary(thread).model_dump(),
        messages=[
            MessageRead(
                id=message.id,
                direction=message.direction,
                subject=message.subject,
                body=message.body,
                email_message_id=message.email_message_id,
                intent=message.intent,
                timestamp=message.timestamp,
            )
            for message in sorted(thread.messages, key=lambda item: item.timestamp)
        ],
        bookings=[
            BookingRead(
                id=booking.id,
                slot=booking.slot,
                status=booking.status,
                cal_event_id=booking.cal_event_id,
                created_at=booking.created_at,
            )
            for booking in sorted(thread.bookings, key=lambda item: item.created_at)
        ],
    )


def _serialize_thread_summary(thread: Thread) -> ThreadSummary:
    """Serialize a thread for list views."""
    sorted_messages = sorted(thread.messages, key=lambda item: item.timestamp)
    last_message_preview = sorted_messages[-1].body[:120] if sorted_messages else None
    return ThreadSummary(
        id=thread.id,
        prospect_email=thread.prospect_email,
        prospect_name=thread.prospect_name,
        status=thread.status,
        config=ThreadConfig.model_validate(thread.config),
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message_preview=last_message_preview,
    )
