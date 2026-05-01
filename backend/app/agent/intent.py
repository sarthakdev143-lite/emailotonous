"""Intent classification for inbound prospect email."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from enum import Enum

from app.config import get_settings
from app.llm_client import LLMUnavailableError, complete

from .prompts import build_intent_system_prompt, build_intent_user_prompt

LOGGER = logging.getLogger(__name__)


class Intent(str, Enum):
    """Supported inbound message intents."""

    INITIAL = "initial"
    INTERESTED = "interested"
    CURIOUS = "curious"
    NEGOTIATING = "negotiating"
    CANCELLATION = "cancellation"
    DECLINING = "declining"
    SILENT = "silent"


KEYWORD_INTENTS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (Intent.CANCELLATION, ("reschedule", "cancel", "move", "another time", "next week")),
    (Intent.DECLINING, ("pass", "not interested", "decline", "can't do it", "no thanks")),
    (Intent.NEGOTIATING, ("rate", "budget", "minimum", "$", "compensation", "worth my time")),
    (Intent.CURIOUS, ("what", "scope", "team", "details", "more about", "company")),
    (Intent.INTERESTED, ("interesting", "interested", "love to learn", "sounds good", "open to it")),
)


async def classify_intent(message_body: str | None, history: Sequence[str] | None = None) -> Intent:
    """Classify the latest prospect message intent with an LLM or keyword fallback."""
    prior_history = list(history or [])
    if message_body is None:
        return Intent.INITIAL if not prior_history else Intent.SILENT

    normalized_body = message_body.strip()
    if not normalized_body:
        return Intent.SILENT

    settings = get_settings()
    if settings.llm_available:
        try:
            raw_result = await complete(
                messages=[{"role": "user", "content": build_intent_user_prompt(normalized_body, prior_history)}],
                system=build_intent_system_prompt(),
            )
            normalized_result = _normalize_intent_label(raw_result)
            if normalized_result is not None:
                return normalized_result
        except LLMUnavailableError:
            LOGGER.info("Intent classification fell back to keywords because no server LLM was available.")

    return _classify_from_keywords(normalized_body)


def _normalize_intent_label(raw_label: str) -> Intent | None:
    """Convert an arbitrary LLM label into a supported intent."""
    normalized = raw_label.strip().lower()
    for intent in Intent:
        if normalized == intent.value:
            return intent
    return None


def _classify_from_keywords(message_body: str) -> Intent:
    """Classify the message with deterministic keyword heuristics."""
    normalized = message_body.lower()
    for intent, keywords in KEYWORD_INTENTS:
        if any(keyword in normalized for keyword in keywords):
            return intent
    return Intent.INTERESTED
