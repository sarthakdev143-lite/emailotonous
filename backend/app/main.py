"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX, APP_NAME, get_settings
from app.database import dispose_database, get_session_maker, init_database
from app.email.inbound import IMAPPoller
from app.routers.agent import router as agent_router
from app.routers.status import router as status_router
from app.routers.threads import router as threads_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources during the app lifecycle."""
    settings = get_settings()
    await init_database()
    scheduler = AsyncIOScheduler()
    app.state.scheduler = scheduler
    if settings.imap_user and settings.imap_password:
        poller = IMAPPoller(get_session_maker())
        app.state.imap_poller = poller
        scheduler.add_job(
            poller.poll_once,
            "interval",
            seconds=settings.imap_poll_interval_seconds,
            id="imap-poll",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await dispose_database()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=APP_NAME, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(status_router, prefix=API_PREFIX)
    app.include_router(threads_router, prefix=API_PREFIX)
    app.include_router(agent_router, prefix=API_PREFIX)
    return app


app = create_app()
