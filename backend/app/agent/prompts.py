"""Prompt builders for the agent and intent classifier."""

from __future__ import annotations

import json
from collections.abc import Sequence


def build_thread_history(history: Sequence[str]) -> str:
    """Format raw message history for prompt inclusion."""
    if not history:
        return "No prior thread history."
    return "\n".join(f"- {entry}" for entry in history)


def build_system_prompt(
    config: dict[str, object], history: Sequence[str], company_name: str
) -> str:
    """Build the structured recruiter system prompt."""
    available_slots = json.dumps(config.get("available_slots", []))
    sections = [
        f"You are a sharp, warm talent acquisition specialist representing {company_name}.",
        f"You are emailing a prospect about a gig: {config.get('gig_description', '')}.",
        "",
        (
            "Your ONLY goal is to get them on a call. "
            "You are NOT a chatbot - you are a human recruiter."
        ),
        "",
        "BUDGET RULES:",
        f"- Our maximum budget is {config.get('budget_ceiling', 0)}.",
        "- You may negotiate but NEVER commit above this ceiling.",
        "- If the prospect's minimum is above ceiling after 2 negotiation turns, call walk_away.",
        "",
        "CONVERSATION RULES:",
        "- Never repeat information already stated in the thread.",
        "- Never contradict a prior commitment.",
        "- Keep emails short (3-5 sentences max unless negotiating).",
        "- Match the prospect's energy.",
        f"- Tone setting: {config.get('tone', 'warm and concise')}",
        "",
        f"AVAILABLE SLOTS: {available_slots}",
        "",
        "FULL THREAD HISTORY:",
        build_thread_history(history),
        "",
        "Based on the latest message, choose exactly ONE tool to call.",
        "Respond ONLY with a single valid JSON object. No markdown, no code fences, no extra text.",
        "",
        "The JSON must use the key 'name' as the discriminator. Valid shapes:",
        '{"name":"send_email","subject":"<string>","body":"<string>"}',
        '{"name":"propose_calendar_slot","body":"<string>","slots":["<ISO datetime>","..."]}',
        '{"name":"walk_away","body":"<string>"}',
        '{"name":"reschedule","body":"<string>","cancelled_slot":"<ISO datetime>","new_slots":["<ISO datetime>","..."]}',
    ]
    return "\n".join(sections)


def build_intent_system_prompt() -> str:
    """Build the strict intent classification system prompt."""
    sections = [
        "You classify recruiter email replies into one label only.",
        "Valid labels: initial, interested, curious, negotiating, cancellation, declining, silent.",
        "Return only the label.",
    ]
    return "\n".join(sections)


def build_intent_user_prompt(message_body: str, history: Sequence[str]) -> str:
    """Build the user prompt for intent classification."""
    return (
        f"History:\n{build_thread_history(history)}\n\n"
        f"Latest message:\n{message_body}\n\n"
        "Return only the intent label."
    )