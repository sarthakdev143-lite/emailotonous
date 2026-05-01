"""LLM provider fallback client."""

from __future__ import annotations

import logging

from groq import AsyncGroq, GroqError
from openai import AsyncOpenAI, OpenAIError

from app.config import GROQ_MODEL, LLM_TEMPERATURE, OPENAI_MODEL, get_settings

LOGGER = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when no usable LLM provider is configured."""


async def complete(messages: list[dict[str, str]], system: str) -> str:
    """Complete a chat request through the configured provider fallback chain."""
    settings = get_settings()
    if settings.openai_api_key:
        try:
            return await _openai_complete(messages=messages, system=system)
        except OpenAIError as error:
            LOGGER.warning("OpenAI completion failed; falling back to Groq if available.", exc_info=error)
    if settings.groq_api_key:
        try:
            return await _groq_complete(messages=messages, system=system)
        except GroqError as error:
            LOGGER.warning("Groq completion failed; no more server-side fallbacks remain.", exc_info=error)
    raise LLMUnavailableError("No API keys configured — use Puter.js fallback")


async def _openai_complete(messages: list[dict[str, str]], system: str) -> str:
    """Complete a chat request with OpenAI."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=LLM_TEMPERATURE,
        messages=[{"role": "system", "content": system}, *messages],
    )
    content = response.choices[0].message.content
    if content is None:
        raise LLMUnavailableError("OpenAI returned an empty response.")
    return content


async def _groq_complete(messages: list[dict[str, str]], system: str) -> str:
    """Complete a chat request with Groq."""
    settings = get_settings()
    client = AsyncGroq(api_key=settings.groq_api_key)
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=LLM_TEMPERATURE,
        messages=[{"role": "system", "content": system}, *messages],
    )
    content = response.choices[0].message.content
    if content is None:
        raise LLMUnavailableError("Groq returned an empty response.")
    return content
