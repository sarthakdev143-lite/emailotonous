"""Configuration parsing tests."""

from __future__ import annotations


def test_settings_parse_csv_cors_origins(monkeypatch) -> None:
    """Allow CSV-style CORS origins from environment settings."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080")

    from app.config import Settings

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://localhost:8080",
    ]
