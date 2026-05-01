"""Resend-backed outbound email service."""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

import requests
import resend

from app.config import get_settings

LOGGER = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when outbound email delivery fails."""


class SupportsEmailSending(Protocol):
    """Protocol for outbound email services."""

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> str:
        """Send an email and return the provider message id."""


class ResendEmailSender:
    """Send outbound email through Resend."""

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> str:
        """Send a plain-text outbound email."""
        settings = get_settings()
        if not settings.resend_api_key:
            raise EmailDeliveryError("RESEND_API_KEY is required for outbound email delivery.")

        resend.api_key = settings.resend_api_key
        headers = {"In-Reply-To": reply_to, "References": reply_to} if reply_to else None
        payload: resend.Emails.SendParams = {
            "from": settings.from_email,
            "to": to_email,
            "subject": subject,
            "text": body,
        }
        if headers is not None:
            payload["headers"] = headers

        try:
            response = await asyncio.to_thread(resend.Emails.send, payload)
        except requests.RequestException as error:
            LOGGER.error("Resend email delivery failed.", exc_info=error)
            raise EmailDeliveryError("Resend email delivery failed.") from error

        return response["id"]
