"""Agent action routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import run_agent_turn
from app.database import get_session
from app.email.outbound import EmailDeliveryError
from app.llm_client import LLMUnavailableError
from app.schemas import PuterProcessRequest, ThreadDetail

router = APIRouter(prefix="/agent", tags=["agent"])

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("/trigger/{thread_id}", response_model=ThreadDetail)
async def trigger_agent(thread_id: str, session: SessionDependency) -> ThreadDetail:
    """Run a manual server-side agent turn for a thread."""
    try:
        return await run_agent_turn(session, thread_id=thread_id)
    except LLMUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmailDeliveryError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/process-puter", response_model=ThreadDetail)
async def process_puter(payload: PuterProcessRequest, session: SessionDependency) -> ThreadDetail:
    """Execute a Puter-produced tool call without invoking a server-side LLM."""
    try:
        return await run_agent_turn(
            session,
            thread_id=payload.thread_id,
            llm_response_override=payload.llm_response,
        )
    except EmailDeliveryError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
