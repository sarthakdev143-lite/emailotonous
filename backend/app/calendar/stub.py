# STUB: This module simulates Cal.com. Replace it with the real Cal.com API for production.
"""Calendar slot generation and booking stub."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BOOKING_STATUS_CANCELLED, BOOKING_STATUS_CONFIRMED, DEFAULT_SLOT_COUNT
from app.models import Booking


class CalendarStub:
    """Mock calendar provider backed by the bookings table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_available_slots(self, count: int = DEFAULT_SLOT_COUNT) -> list[str]:
        """Return a predictable set of future business-hour slots."""
        start_day = datetime.now().astimezone() + timedelta(days=2)
        business_hours = [time(hour=10), time(hour=14), time(hour=16)]
        slots: list[str] = []
        day_offset = 0
        while len(slots) < count:
            current_day = (start_day + timedelta(days=day_offset)).date()
            for business_hour in business_hours:
                slot = datetime.combine(current_day, business_hour, tzinfo=start_day.tzinfo)
                slots.append(slot.isoformat())
                if len(slots) == count:
                    break
            day_offset += 1
        return slots

    async def book_slot(self, thread_id: str, slot: str) -> str:
        """Persist a mock booking and return a synthetic event id."""
        event_id = f"cal_{uuid4()}"
        booking = Booking(
            id=str(uuid4()),
            thread_id=thread_id,
            slot=slot,
            status=BOOKING_STATUS_CONFIRMED,
            cal_event_id=event_id,
        )
        self.session.add(booking)
        await self.session.flush()
        return event_id

    async def cancel_slot(self, event_id: str) -> bool:
        """Mark a booking as cancelled if it exists."""
        result = await self.session.execute(select(Booking).where(Booking.cal_event_id == event_id))
        booking = result.scalar_one_or_none()
        if booking is None:
            return False
        booking.status = BOOKING_STATUS_CANCELLED
        await self.session.flush()
        return True
