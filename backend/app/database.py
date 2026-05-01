"""Async database engine and session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


@lru_cache
def get_engine() -> AsyncEngine:
    """Create and cache the async SQLAlchemy engine."""
    return create_async_engine(get_settings().database_url, future=True, echo=get_settings().debug)


@lru_cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with get_session_maker()() as session:
        yield session


async def init_database() -> None:
    """Create database tables for local development and tests."""
    from app import models  # noqa: F401

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_database() -> None:
    """Dispose the async database engine."""
    await get_engine().dispose()


def reset_database_state() -> None:
    """Clear cached engine and session state for tests."""
    get_session_maker.cache_clear()
    get_engine.cache_clear()
