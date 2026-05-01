# Email Wake-Up Agent — Codex Build Prompt

## Project Overview

Build a production-ready **Email Wake-Up Agent** — an autonomous AI agent that cold-emails prospects about a job gig, holds a natural conversation, negotiates budget, and books a call. The agent must handle reschedule loops gracefully (N times) with full conversation memory.

---

## Tech Stack (non-negotiable)

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Best practice for AI agent projects |
| Email Outbound | Resend API | Simplest reliable transactional email |
| Email Inbound | IMAP polling (imaplib) | Works with any real inbox |
| LLM | OpenAI GPT-4o → Groq → Puter.js | See fallback chain below |
| Database | SQLite via SQLAlchemy (async) | Zero setup, portable, demo-friendly |
| Calendar | Cal.com stub (clearly marked) | Swappable to real integration |
| Frontend | React (Vite) + Tailwind CSS | Thread dashboard + Puter.js fallback |
| Task Queue | APScheduler (in-process) | IMAP polling every 60s |

---

## LLM Fallback Chain

Implement a single `llm_client.py` module that tries providers in order:

```
1. OpenAI GPT-4o       — if OPENAI_API_KEY is set
2. Groq (llama-3.3-70b-versatile) — if GROQ_API_KEY is set (FREE)
3. Puter.js            — frontend-driven fallback (completely FREE, no API key)
```

### Puter.js Fallback
- When backend has no API keys available, it returns `{"llm_available": false}` on `/api/status`
- The React frontend detects this and loads Puter.js (`<script src="https://js.puter.com/v2/"></script>`)
- Frontend calls `puter.ai.chat(prompt)` directly and posts the result to `/api/agent/process-puter`
- Backend endpoint `/api/agent/process-puter` accepts `{thread_id, llm_response}` and executes the action layer (send email, update DB) without calling LLM itself

```python
# llm_client.py
async def complete(messages: list[dict], system: str) -> str:
    if settings.OPENAI_API_KEY:
        return await _openai_complete(messages, system)
    if settings.GROQ_API_KEY:
        return await _groq_complete(messages, system)
    raise LLMUnavailableError("No API keys configured — use Puter.js fallback")
```

---

## Project Structure

```
email-wakeup-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, lifespan, routers
│   │   ├── config.py                # Pydantic Settings, .env loading
│   │   ├── database.py              # SQLAlchemy async engine + session
│   │   ├── models.py                # Thread, Message ORM models
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── llm_client.py            # OpenAI → Groq → raise LLMUnavailableError
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── core.py              # Main agent loop: perceive → reason → act
│   │   │   ├── prompts.py           # All system/user prompt templates
│   │   │   ├── tools.py             # Tool definitions: send_email, propose_slot, walk_away, reschedule
│   │   │   └── intent.py            # Intent classifier (interested/negotiating/cancellation/declining/silent)
│   │   ├── email/
│   │   │   ├── __init__.py
│   │   │   ├── outbound.py          # Resend API sender
│   │   │   └── inbound.py           # IMAP poller, reply parser, thread matcher
│   │   ├── calendar/
│   │   │   ├── __init__.py
│   │   │   └── stub.py              # Cal.com stub — returns mock slots, logs bookings
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── threads.py           # GET /api/threads, GET /api/threads/{id}
│   │       ├── agent.py             # POST /api/agent/trigger, POST /api/agent/process-puter
│   │       └── status.py            # GET /api/status — health + LLM availability
│   ├── tests/
│   │   ├── test_intent.py
│   │   ├── test_agent_core.py
│   │   └── test_reschedule_loop.py
│   ├── alembic/                     # DB migrations
│   ├── config.example.env           # Template .env — never commit real .env
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── client.ts            # Axios API client
│   │   ├── components/
│   │   │   ├── ThreadList.tsx
│   │   │   ├── ThreadDetail.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   └── PuterFallback.tsx    # Puter.js UI when no backend LLM keys
│   │   ├── hooks/
│   │   │   └── useAgentStatus.ts
│   │   └── types/
│   │       └── index.ts
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docker-compose.yml               # One-command setup
├── .gitignore
└── README.md                        # Root README with full setup guide
```

---

## Database Schema

```sql
-- threads table
CREATE TABLE threads (
    id          TEXT PRIMARY KEY,          -- UUID
    prospect_email  TEXT NOT NULL,
    prospect_name   TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    -- status ENUM: pending | outreach_sent | negotiating | slot_proposed | booked | closed_no_fit | closed_no_reply
    config      TEXT NOT NULL,             -- JSON: gig_description, budget_ceiling, tone, available_slots
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- messages table
CREATE TABLE messages (
    id          TEXT PRIMARY KEY,          -- UUID
    thread_id   TEXT NOT NULL REFERENCES threads(id),
    direction   TEXT NOT NULL,             -- 'outbound' | 'inbound'
    subject     TEXT,
    body        TEXT NOT NULL,
    email_message_id TEXT,                 -- RFC 2822 Message-ID for threading
    intent      TEXT,                      -- detected intent for inbound messages
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- bookings table
CREATE TABLE bookings (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL REFERENCES threads(id),
    slot        TEXT NOT NULL,             -- ISO datetime string
    status      TEXT NOT NULL DEFAULT 'confirmed',  -- confirmed | cancelled | rescheduled
    cal_event_id TEXT,                     -- stub or real Cal.com event ID
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## Agent Core Design

### Perception → Reasoning → Action Loop

```python
# agent/core.py
async def run_agent_turn(thread_id: str, new_message: Message | None = None):
    """
    Single agent turn triggered by:
    - New inbound email (new_message is set)
    - Manual trigger for initial outreach (new_message is None)
    """
    thread = await get_thread(thread_id)
    history = await get_all_messages(thread_id)
    config = thread.config  # gig_description, budget_ceiling, tone, available_slots

    # 1. PERCEIVE — classify intent of latest inbound
    intent = await classify_intent(new_message, history) if new_message else Intent.INITIAL

    # 2. REASON — call LLM with full context
    system_prompt = build_system_prompt(config)
    conversation = build_conversation_history(history)
    llm_response = await llm_client.complete(conversation, system_prompt)

    # 3. ACT — parse tool call from LLM response, execute
    action = parse_tool_call(llm_response)
    await execute_action(action, thread, config)

    # 4. PERSIST — save outbound message, update thread status
    await save_outbound_message(thread_id, action.email_body)
    await update_thread_status(thread_id, derive_status(intent, action))
```

### Tools the LLM Can Call

```python
tools = [
    {
        "name": "send_email",
        "description": "Send an email reply to the prospect",
        "parameters": {
            "subject": "string",
            "body": "string — natural, human-sounding email body"
        }
    },
    {
        "name": "propose_calendar_slot",
        "description": "Propose specific time slots for a call",
        "parameters": {
            "body": "string — email body with embedded slot proposals",
            "slots": ["ISO datetime strings"]
        }
    },
    {
        "name": "walk_away",
        "description": "Gracefully close the conversation when there is no budget fit or explicit decline",
        "parameters": {
            "body": "string — polite, warm closing email"
        }
    },
    {
        "name": "reschedule",
        "description": "Acknowledge cancellation and propose new slots",
        "parameters": {
            "body": "string",
            "cancelled_slot": "ISO datetime",
            "new_slots": ["ISO datetime strings"]
        }
    }
]
```

### System Prompt Template

```
You are a sharp, warm talent acquisition specialist representing {company_name}.
You are emailing {prospect_name} about a gig: {gig_description}.

Your ONLY goal is to get them on a call. You are NOT a chatbot — you are a human recruiter.

BUDGET RULES:
- Our maximum budget is {budget_ceiling}.
- You may negotiate but NEVER commit above this ceiling.
- If the prospect's minimum is above ceiling after 2 negotiation turns, call walk_away.

CONVERSATION RULES:
- Never repeat information already stated in the thread.
- Never contradict a prior commitment.
- Keep emails short (3–5 sentences max unless negotiating).
- Match the prospect's energy — if they're casual, be casual.
- Tone setting: {tone}

AVAILABLE SLOTS: {available_slots}

FULL THREAD HISTORY:
{formatted_thread_history}

Based on the latest message, choose exactly ONE tool to call.
Respond ONLY with a valid JSON tool call object. No extra text.
```

---

## Intent Classification

```python
# agent/intent.py
class Intent(str, Enum):
    INITIAL = "initial"
    INTERESTED = "interested"
    CURIOUS = "curious"
    NEGOTIATING = "negotiating"
    CANCELLATION = "cancellation"     # THE CRITICAL LOOP TRIGGER
    DECLINING = "declining"
    SILENT = "silent"

async def classify_intent(message: Message, history: list[Message]) -> Intent:
    """
    Lightweight LLM call (or Groq) to classify inbound email intent.
    Uses a strict prompt that returns only the intent label.
    Falls back to keyword matching if LLM unavailable.
    """
```

---

## Email Inbound (IMAP Polling)

```python
# email/inbound.py
class IMAPPoller:
    """Polls inbox every 60s, matches emails to threads by In-Reply-To header."""

    def match_thread(self, email_msg) -> str | None:
        """
        Match inbound email to a thread using:
        1. In-Reply-To / References headers (primary)
        2. Subject line thread matching (fallback)
        3. Sender email match against open threads (last resort)
        """

    async def process_new_email(self, raw_email, thread_id: str):
        """Save inbound message, trigger agent turn."""
```

---

## Calendar Stub

```python
# calendar/stub.py
# STUB: This module simulates Cal.com. Replace with real Cal.com API for production.

class CalendarStub:
    async def get_available_slots(self, count: int = 3) -> list[str]:
        """Returns {count} mock slots starting 2 days from now, business hours."""

    async def book_slot(self, thread_id: str, slot: str) -> str:
        """Logs booking to bookings table. Returns mock event ID."""

    async def cancel_slot(self, event_id: str) -> bool:
        """Marks booking as cancelled."""
```

---

## API Endpoints

```
GET  /api/status                     → { healthy, llm_provider, llm_available }
GET  /api/threads                    → List[ThreadSummary]
GET  /api/threads/{id}               → ThreadDetail with all messages
POST /api/threads                    → Create new thread (prospect_email, config)
POST /api/agent/trigger/{thread_id}  → Manually trigger agent turn (sends initial outreach)
POST /api/agent/process-puter        → { thread_id, llm_response } — Puter.js path
POST /api/email/webhook              → (optional) Resend inbound webhook
```

---

## Frontend (React Dashboard)

Build a clean dashboard with:

1. **Thread List** — left panel showing all threads with status badges and last message preview
2. **Thread Detail** — right panel showing full message history as chat bubbles (inbound left, outbound right)
3. **Trigger Panel** — form to create new thread (prospect email, gig config override, manual trigger button)
4. **Status Bar** — shows which LLM provider is active (OpenAI / Groq / Puter.js)
5. **PuterFallback Component** — renders only when `/api/status` returns `llm_available: false`. Loads Puter.js script dynamically, shows a notice "Running on Puter.js (free mode)", handles the `puter.ai.chat()` call and posts result back to `/api/agent/process-puter`

---

## Configuration (.env)

```env
# LLM — set at least one, or leave all blank for Puter.js
OPENAI_API_KEY=
GROQ_API_KEY=

# Email — Resend outbound
RESEND_API_KEY=
FROM_EMAIL=agent@yourdomain.com

# Email — IMAP inbound
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=
IMAP_PASSWORD=
IMAP_POLL_INTERVAL_SECONDS=60

# App
DATABASE_URL=sqlite+aiosqlite:///./agent.db
SECRET_KEY=change-me
DEBUG=false
```

---

## Sample Transcripts Required

Create `/samples/` directory with three JSON files:

1. `successful_booking.json` — negotiation → slot proposed → booked
2. `reschedule_loop.json` — booked → cancelled → rebooked (at least twice)
3. `graceful_walkaway.json` — prospect below budget floor → polite close

Each file must be an array of `{direction, body, intent, timestamp}` objects representing a real-looking conversation.

---

## Tests Required

```
tests/test_intent.py          — test each Intent classification with mock email bodies
tests/test_agent_core.py      — test agent turn produces correct tool call for each intent
tests/test_reschedule_loop.py — simulate N cancellations, assert thread stays coherent
```

---

## README Requirements

Root README must include:
1. Architecture diagram (ASCII or Mermaid)
2. Setup instructions (works from scratch in < 5 commands)
3. How to run with each LLM option (OpenAI / Groq / Puter.js)
4. How to test the reschedule loop manually
5. Trade-offs and known limitations section
6. How to swap calendar stub for real Cal.com
