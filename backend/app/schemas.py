"""Pydantic request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StatusResponse(BaseModel):
    """API status response payload."""

    healthy: bool
    llm_available: bool
    llm_provider: str


class ThreadConfig(BaseModel):
    """Thread-specific recruiter configuration."""

    gig_description: str
    budget_ceiling: int = Field(ge=0)
    tone: str
    available_slots: list[str]


class ThreadCreate(BaseModel):
    """Payload for creating a new conversation thread."""

    prospect_email: EmailStr
    prospect_name: str | None = None
    config: ThreadConfig


class MessageRead(BaseModel):
    """Serialized message payload."""

    id: str
    direction: str
    subject: str | None
    body: str
    email_message_id: str | None
    intent: str | None
    timestamp: datetime


class BookingRead(BaseModel):
    """Serialized booking payload."""

    id: str
    slot: str
    status: str
    cal_event_id: str | None
    created_at: datetime


class ThreadSummary(BaseModel):
    """Thread list row payload."""

    id: str
    prospect_email: EmailStr
    prospect_name: str | None
    status: str
    config: ThreadConfig
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None


class ThreadDetail(ThreadSummary):
    """Detailed thread response including messages and bookings."""

    messages: list[MessageRead]
    bookings: list[BookingRead]


class PuterProcessRequest(BaseModel):
    """Payload for frontend-driven Puter responses."""

    thread_id: str
    llm_response: str
