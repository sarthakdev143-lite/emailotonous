"""Status router."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import StatusResponse

router = APIRouter(prefix="/status", tags=["status"])


@router.get("", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Return backend health and LLM availability."""
    settings = get_settings()
    return StatusResponse(
        healthy=True,
        llm_available=settings.llm_available,
        llm_provider=settings.llm_provider,
    )
