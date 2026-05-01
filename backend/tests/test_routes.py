"""API route integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    """Create an API client backed by an isolated database."""
    from app.config import get_settings
    from app.database import dispose_database, init_database, reset_database_state
    from app.main import create_app

    database_path = tmp_path / "routes.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.resolve().as_posix()}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_database_state()
    await init_database()

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client

    await dispose_database()
    reset_database_state()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_create_and_fetch_thread_routes(client: AsyncClient) -> None:
    """Create a thread and fetch it back through the API."""
    create_response = await client.post(
        "/api/threads",
        json={
            "prospect_email": "prospect@example.com",
            "prospect_name": "Robin Recruit",
            "config": {
                "gig_description": "Lifecycle email sprint",
                "budget_ceiling": 4500,
                "tone": "warm and clear",
                "available_slots": [
                    "2026-05-05T10:00:00+05:30",
                    "2026-05-05T14:00:00+05:30",
                    "2026-05-06T11:00:00+05:30",
                ],
            },
        },
    )

    thread_payload = create_response.json()
    detail_response = await client.get(f"/api/threads/{thread_payload['id']}")

    assert create_response.status_code == 201
    assert thread_payload["status"] == "pending"
    assert detail_response.status_code == 200
    assert detail_response.json()["prospect_email"] == "prospect@example.com"


@pytest.mark.asyncio
async def test_list_threads_route_returns_created_threads(client: AsyncClient) -> None:
    """List threads should include newly created threads."""
    await client.post(
        "/api/threads",
        json={
            "prospect_email": "first@example.com",
            "prospect_name": "First Prospect",
            "config": {
                "gig_description": "Lifecycle email sprint",
                "budget_ceiling": 4500,
                "tone": "warm and clear",
                "available_slots": ["2026-05-05T10:00:00+05:30"],
            },
        },
    )
    await client.post(
        "/api/threads",
        json={
            "prospect_email": "second@example.com",
            "prospect_name": "Second Prospect",
            "config": {
                "gig_description": "Follow-up automation sprint",
                "budget_ceiling": 5500,
                "tone": "warm and direct",
                "available_slots": ["2026-05-07T10:00:00+05:30"],
            },
        },
    )

    response = await client.get("/api/threads")
    payload = response.json()

    assert response.status_code == 200
    assert len(payload) == 2
    assert {thread["prospect_email"] for thread in payload} == {
        "first@example.com",
        "second@example.com",
    }


@pytest.mark.asyncio
async def test_process_puter_route_executes_action_without_server_llm(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Puter route should persist the action layer response directly."""

    async def fake_send_email(
        self: object,
        *,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> str:
        return "puter-message-1"

    monkeypatch.setattr("app.email.outbound.ResendEmailSender.send_email", fake_send_email)

    create_response = await client.post(
        "/api/threads",
        json={
            "prospect_email": "puter@example.com",
            "prospect_name": "Puter Prospect",
            "config": {
                "gig_description": "Growth email sprint",
                "budget_ceiling": 5000,
                "tone": "warm and clear",
                "available_slots": ["2026-05-08T10:00:00+05:30"],
            },
        },
    )
    thread_id = create_response.json()["id"]

    response = await client.post(
        "/api/agent/process-puter",
        json={
            "thread_id": thread_id,
            "llm_response": json.dumps(
                {
                    "name": "send_email",
                    "subject": "Growth sprint role",
                    "body": "Would you be open to a quick intro call this week?",
                }
            ),
        },
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "outreach_sent"
    assert payload["messages"][-1]["body"] == "Would you be open to a quick intro call this week?"


@pytest.mark.asyncio
async def test_trigger_route_returns_503_without_server_llm(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manual trigger should report when no server-side LLM is available."""
    create_response = await client.post(
        "/api/threads",
        json={
            "prospect_email": "trigger@example.com",
            "prospect_name": "Trigger Prospect",
            "config": {
                "gig_description": "Growth email sprint",
                "budget_ceiling": 5000,
                "tone": "warm and clear",
                "available_slots": ["2026-05-08T10:00:00+05:30"],
            },
        },
    )
    thread_id = create_response.json()["id"]

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = await client.post(f"/api/agent/trigger/{thread_id}")

    assert response.status_code == 503
