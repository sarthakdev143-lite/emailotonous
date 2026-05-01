"""Status endpoint tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_status_reports_puter_mode_when_no_server_llm_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the Puter fallback status when no server-side keys are configured."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/status")

    payload = response.json()

    assert response.status_code == 200
    assert payload == {
        "healthy": True,
        "llm_available": False,
        "llm_provider": "puter",
    }


@pytest.mark.asyncio
async def test_status_reports_openai_when_openai_key_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose the active provider when the OpenAI key exists."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/status")

    payload = response.json()

    assert response.status_code == 200
    assert payload == {
        "healthy": True,
        "llm_available": True,
        "llm_provider": "openai",
    }
