"""Scheduler integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_app_lifespan_registers_imap_poll_job_when_credentials_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start the in-process IMAP scheduler when credentials are configured."""
    from app.config import get_settings
    from app.database import reset_database_state
    from app.main import create_app

    async def fake_poll_once(self: object) -> int:
        return 0

    database_path = tmp_path / "scheduler.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.resolve().as_posix()}")
    monkeypatch.setenv("IMAP_USER", "agent@example.com")
    monkeypatch.setenv("IMAP_PASSWORD", "test-password")
    monkeypatch.setenv("IMAP_POLL_INTERVAL_SECONDS", "30")
    monkeypatch.setattr("app.email.inbound.IMAPPoller.poll_once", fake_poll_once)
    get_settings.cache_clear()
    reset_database_state()

    app = create_app()

    async with app.router.lifespan_context(app):
        jobs = app.state.scheduler.get_jobs()
        assert any(job.id == "imap-poll" for job in jobs)
