# Email Wake-Up Agent Design

## Goal

Build a production-ready Email Wake-Up Agent with a FastAPI backend, React dashboard, SQLite persistence, outbound email through Resend, inbound email polling through IMAP, and an LLM fallback chain of OpenAI to Groq to Puter.js.

## Architecture

The system is split into a backend service and a frontend dashboard. The backend owns thread persistence, inbound and outbound email coordination, scheduling, intent classification, the agent reasoning loop, and the action layer. The frontend presents thread state, creates new threads, triggers outreach, and takes over the reasoning step through Puter.js when the backend has no server-side API key configured.

The backend follows a strict perceive, reason, act flow. Each agent turn loads the full thread history, classifies the latest inbound message intent, builds a structured system prompt, asks the LLM for exactly one tool call, executes that tool, persists new messages and bookings, and updates the thread state through a controlled state machine.

The frontend uses a two-panel dashboard layout. It polls API state for threads and LLM availability, shows each conversation as a recruiter-style message thread, and renders a Puter.js action panel only when `/api/status` reports `llm_available: false`.

## Components

- `app/config.py`: central settings and constants through `BaseSettings`
- `app/database.py`: async engine, async session maker, lifecycle helpers
- `app/models.py`: SQLAlchemy 2.0 models for threads, messages, bookings
- `app/schemas.py`: request and response contracts for API endpoints
- `app/llm_client.py`: OpenAI to Groq fallback chain plus availability helpers
- `app/agent/*`: prompts, tool models, intent detection, action orchestration
- `app/email/*`: Resend sender and IMAP polling pipeline
- `app/calendar/stub.py`: mock calendar provider with booking persistence
- `app/routers/*`: API surface for status, threads, agent actions, and email intake
- `frontend/src/*`: dashboard shell, API client, hooks, typed components, Puter fallback

## Data Flow

1. A user creates a thread from the dashboard with the prospect details and gig configuration.
2. A manual trigger or inbound email starts an agent turn.
3. The agent loads the full thread and classifies the newest message.
4. If server-side LLM access exists, the backend reasons and executes the selected tool.
5. If no server-side LLM access exists, the backend exposes `llm_available: false`, the frontend asks Puter.js for the tool JSON, and the backend executes the returned action through `/api/agent/process-puter`.
6. Every action persists messages, bookings, and state transitions before returning API data to the dashboard.

## Error Handling

- LLM provider errors fall through the provider chain or surface a controlled `LLMUnavailableError`.
- Route handlers return `404` for missing threads and `503` when no server-side or Puter path can proceed.
- Email delivery and IMAP polling failures are logged and retried or deferred without crashing the app.
- Calendar booking and cancellation failures raise typed errors and preserve thread consistency.

## Testing

The backend test suite focuses on offline behavior with mocked integrations. Intent tests validate both keyword fallback and edge cases. Agent core tests validate structured tool selection and status transitions. The reschedule loop test simulates five cancellations to ensure coherent conversation state across repeated rebooking cycles.

## Constraints

- No top-level directories beyond the prompt structure.
- No secrets committed.
- Backend stays async throughout.
- Frontend uses typed API access through a single client module.
- The agent sends at most one email per turn and always reasons over full history.
