"""Structured tool call definitions for agent actions."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError


class ToolParseError(ValueError):
    """Raised when an LLM tool payload is invalid."""


class SendEmailAction(BaseModel):
    """Send a plain outbound email."""

    name: Literal["send_email"]
    subject: str
    body: str


class ProposeCalendarSlotAction(BaseModel):
    """Propose one or more call slots."""

    name: Literal["propose_calendar_slot"]
    body: str
    slots: list[str]


class WalkAwayAction(BaseModel):
    """Close the thread when there is no budget fit."""

    name: Literal["walk_away"]
    body: str


class RescheduleAction(BaseModel):
    """Reschedule an already booked call."""

    name: Literal["reschedule"]
    body: str
    cancelled_slot: str
    new_slots: list[str]


AgentAction = Annotated[
    SendEmailAction | ProposeCalendarSlotAction | WalkAwayAction | RescheduleAction,
    Field(discriminator="name"),
]

TOOL_CALL_ADAPTER = TypeAdapter(AgentAction)


def parse_tool_call(raw_response: str) -> AgentAction:
    """Parse a raw JSON tool call into a typed action."""
    try:
        payload = json.loads(raw_response)
        return TOOL_CALL_ADAPTER.validate_python(payload)
    except (json.JSONDecodeError, ValidationError) as error:
        raise ToolParseError("Invalid agent tool call payload.") from error
