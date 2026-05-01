"""Inbound email polling and thread matching."""

from __future__ import annotations

import asyncio
import imaplib
import logging
from dataclasses import dataclass
from email import message_from_bytes
from email.message import EmailMessage, Message
from email.policy import default as default_email_policy
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.agent.core import add_inbound_message, run_agent_turn
from app.config import (
    THREAD_STATUS_CLOSED_NO_FIT,
    THREAD_STATUS_CLOSED_NO_REPLY,
    get_settings,
)
from app.models import Message as ThreadMessage
from app.models import Thread

LOGGER = logging.getLogger(__name__)

REPLY_PREFIXES = ("re:", "fw:", "fwd:")


@dataclass(slots=True)
class ThreadCandidate:
    """Minimal thread context used for IMAP matching."""

    thread_id: str
    prospect_email: str
    subject: str | None
    status: str
    message_ids: list[str]


class IMAPPoller:
    """Poll an IMAP inbox and route replies into existing threads."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | Callable[[], Any]) -> None:
        self.session_factory = session_factory

    def match_thread(
        self,
        email_msg: Message,
        thread_candidates: list[ThreadCandidate] | None = None,
    ) -> str | None:
        """Match an inbound message to a known thread using headers then fallbacks."""
        candidates = thread_candidates or []
        in_reply_to = email_msg.get("In-Reply-To")
        references = email_msg.get("References", "")
        sender = self._extract_sender_email(email_msg.get("From", ""))
        normalized_subject = self._normalize_subject(email_msg.get("Subject"))

        if in_reply_to is not None:
            for candidate in candidates:
                if in_reply_to in candidate.message_ids:
                    return candidate.thread_id

        if references:
            reference_ids = {part.strip() for part in references.split() if part.strip()}
            for candidate in candidates:
                if reference_ids.intersection(candidate.message_ids):
                    return candidate.thread_id

        for candidate in candidates:
            if self._normalize_subject(candidate.subject) == normalized_subject and normalized_subject:
                return candidate.thread_id

        for candidate in candidates:
            if candidate.prospect_email.lower() == sender and candidate.status not in {
                THREAD_STATUS_CLOSED_NO_FIT,
                THREAD_STATUS_CLOSED_NO_REPLY,
            }:
                return candidate.thread_id

        return None

    async def process_new_email(self, raw_email: bytes, thread_id: str) -> None:
        """Persist an inbound email and trigger the next agent turn."""
        email_message = message_from_bytes(raw_email, policy=default_email_policy)
        body = self._extract_body(email_message)
        async with self.session_factory() as session:
            await add_inbound_message(
                session,
                thread_id=thread_id,
                subject=email_message.get("Subject"),
                body=body,
                email_message_id=email_message.get("Message-ID"),
            )
            await run_agent_turn(session, thread_id=thread_id)

    async def poll_once(self) -> int:
        """Poll the IMAP inbox once and process matching unseen replies."""
        settings = get_settings()
        if not settings.imap_user or not settings.imap_password:
            LOGGER.info("IMAP credentials are not configured; skipping poll cycle.")
            return 0

        try:
            raw_messages = await asyncio.to_thread(self._fetch_unseen_messages)
        except (imaplib.IMAP4.error, OSError) as error:
            LOGGER.warning("IMAP polling failed and will retry on the next cycle.", exc_info=error)
            return 0

        processed_count = 0
        async with self.session_factory() as session:
            candidates = await self._load_thread_candidates(session)
        for raw_message in raw_messages:
            email_message = message_from_bytes(raw_message, policy=default_email_policy)
            thread_id = self.match_thread(email_message, candidates)
            if thread_id is None:
                LOGGER.info("Ignoring unmatched inbound email with subject '%s'.", email_message.get("Subject"))
                continue
            await self.process_new_email(raw_message, thread_id)
            processed_count += 1
        return processed_count

    async def _load_thread_candidates(self, session: AsyncSession) -> list[ThreadCandidate]:
        """Load open thread metadata for matching inbound email."""
        result = await session.execute(
            select(Thread)
            .options(selectinload(Thread.messages))
            .where(Thread.status.not_in((THREAD_STATUS_CLOSED_NO_FIT, THREAD_STATUS_CLOSED_NO_REPLY)))
        )
        threads = result.scalars().all()
        return [
            ThreadCandidate(
                thread_id=thread.id,
                prospect_email=thread.prospect_email,
                subject=self._latest_subject(thread.messages),
                status=thread.status,
                message_ids=[message.email_message_id for message in thread.messages if message.email_message_id],
            )
            for thread in threads
        ]

    def _fetch_unseen_messages(self) -> list[bytes]:
        """Fetch unseen messages from the configured IMAP inbox."""
        settings = get_settings()
        client = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        try:
            client.login(settings.imap_user, settings.imap_password)
            client.select("INBOX")
            _, message_numbers = client.search(None, "UNSEEN")
            raw_messages: list[bytes] = []
            for message_number in message_numbers[0].split():
                _, payload = client.fetch(message_number, "(RFC822)")
                if payload and isinstance(payload[0], tuple):
                    raw_messages.append(payload[0][1])
            return raw_messages
        finally:
            try:
                client.close()
            except imaplib.IMAP4.error:
                LOGGER.debug("IMAP mailbox was already closed.")
            client.logout()

    @staticmethod
    def _extract_sender_email(raw_from_header: str) -> str:
        """Extract a lowercase sender address from a From header."""
        if "<" in raw_from_header and ">" in raw_from_header:
            return raw_from_header.split("<", maxsplit=1)[1].split(">", maxsplit=1)[0].strip().lower()
        return raw_from_header.strip().lower()

    @staticmethod
    def _normalize_subject(subject: str | None) -> str:
        """Normalize subject text for thread matching."""
        if subject is None:
            return ""
        normalized = subject.strip().lower()
        changed = True
        while changed:
            changed = False
            for prefix in REPLY_PREFIXES:
                if normalized.startswith(prefix):
                    normalized = normalized[len(prefix) :].strip()
                    changed = True
        return normalized

    @staticmethod
    def _latest_subject(messages: list[ThreadMessage]) -> str | None:
        """Return the newest non-empty subject in a thread."""
        for message in sorted(messages, key=lambda item: item.timestamp, reverse=True):
            if message.subject:
                return message.subject
        return None

    @staticmethod
    def _extract_body(email_message: Message) -> str:
        """Extract a plain-text body from a parsed email message."""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not part.get_filename():
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        if isinstance(email_message, EmailMessage):
            content = email_message.get_content()
            return content if isinstance(content, str) else content.decode("utf-8", errors="replace")
        payload = email_message.get_payload(decode=True) or b""
        return payload.decode("utf-8", errors="replace")
