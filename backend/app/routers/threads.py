"""Thread management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import create_thread, get_thread_detail, list_threads
from app.database import get_session
from app.schemas import ThreadCreate, ThreadDetail, ThreadSummary

router = APIRouter(prefix="/threads", tags=["threads"])

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[ThreadSummary])
async def get_threads(session: SessionDependency) -> list[ThreadSummary]:
    """Return all threads for the dashboard list."""
    return await list_threads(session)


@router.get("/{thread_id}", response_model=ThreadDetail)
async def get_thread(thread_id: str, session: SessionDependency) -> ThreadDetail:
    """Return a single thread with full message history."""
    return await get_thread_detail(session, thread_id)


@router.post("", response_model=ThreadDetail, status_code=status.HTTP_201_CREATED)
async def post_thread(payload: ThreadCreate, session: SessionDependency) -> ThreadDetail:
    """Create a new prospect thread."""
    thread = await create_thread(session, payload)
    return await get_thread_detail(session, thread.id)
