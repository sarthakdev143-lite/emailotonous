"""Prompt builders for the agent and intent classifier."""

from __future__ import annotations

import json
from collections.abc import Sequence


def build_thread_history(history: Sequence[str]) -> str:
    """Format raw message history for prompt inclusion."""
    if not history:
        return "No prior thread history."
    return "\n".join(f"- {entry}" for entry in history)


def build_system_prompt(config: dict[str, object], history: Sequence[str], company_name: str) -> str:
    """Build the structured recruiter system prompt."""
    available_slots = json.dumps(config.get("available_slots", []))
    return (
        f"You are a sharp, warm talent acquisition specialist representing {company_name}.\n"
        f"You are emailing a prospect about a gig: {config.get('gig_description', '')}.\n\n"
        "Your ONLY goal is to get them on a call. You are NOT a chatbot — you are a human recruiter.\n\n"
        "BUDGET RULES:\n"
        f"- Our maximum budget is {config.get('budget_ceiling', 0)}.\n"
        "- You may negotiate but NEVER commit above this ceiling.\n"
        "- If the prospect's minimum is above ceiling after 2 negotiation turns, call walk_away.\n\n"
        "CONVERSATION RULES:\n"
        "- Never repeat information already stated in the thread.\n"
        "- Never contradict a prior commitment.\n"
        "- Keep emails short (3-5 sentences max unless negotiating).\n"
        "- Match the prospect's energy.\n"
        f"- Tone setting: {config.get('tone', 'warm and concise')}\n\n"
        f"AVAILABLE SLOTS: {available_slots}\n\n"
        "FULL THREAD HISTORY:\n"
        f"{build_thread_history(history)}\n\n"
        "Based on the latest message, choose exactly ONE tool to call.\n"
        "Respond ONLY with a valid JSON tool call object. No extra text."
    )


def build_intent_system_prompt() -> str:
    """Build the strict intent classification system prompt."""
    return (
        "You classify recruiter email replies into one label only.\n"
        "Valid labels: initial, interested, curious, negotiating, cancellation, declining, silent.\n"
        "Return only the label."
    )


def build_intent_user_prompt(message_body: str, history: Sequence[str]) -> str:
    """Build the user prompt for intent classification."""
    return (
        f"History:\n{build_thread_history(history)}\n\n"
        f"Latest message:\n{message_body}\n\n"
        "Return only the intent label."
    )
