# Email Wake-Up Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete Email Wake-Up Agent stack from the approved prompt, including backend, frontend, Docker, samples, and offline tests.

**Architecture:** Build the project in vertical slices so every commit leaves the repository runnable. Start with repository scaffolding and backend primitives, then layer in agent behavior, integrations, frontend UI, infrastructure, and documentation.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, SQLite, APScheduler, React, Vite, Tailwind CSS, TypeScript, Axios, Docker Compose, nginx

---

### Task 1: Repository and dependency scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.example.env`
- Create: `backend/pyproject.toml`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`

- [ ] Add pinned backend and frontend dependencies.
- [ ] Add formatter and linter configuration for Python and TypeScript.
- [ ] Commit the clean scaffold.

### Task 2: Backend foundation with TDD

**Files:**
- Create: `backend/tests/test_status.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/status.py`

- [ ] Write failing tests for the health and status contract.
- [ ] Implement settings, async database wiring, and base FastAPI app.
- [ ] Add status route and verify the tests pass.
- [ ] Commit the working backend foundation.

### Task 3: Intent and LLM pipeline with TDD

**Files:**
- Create: `backend/tests/test_intent.py`
- Create: `backend/app/llm_client.py`
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/intent.py`
- Create: `backend/app/agent/prompts.py`
- Create: `backend/app/agent/tools.py`

- [ ] Write failing tests for intent classification behavior.
- [ ] Implement fallback keyword classification and LLM provider selection.
- [ ] Add structured tool call parsing and status derivation helpers.
- [ ] Commit the LLM and intent slice.

### Task 4: Agent actions, email, and calendar flow

**Files:**
- Create: `backend/tests/test_agent_core.py`
- Create: `backend/app/agent/core.py`
- Create: `backend/app/email/__init__.py`
- Create: `backend/app/email/outbound.py`
- Create: `backend/app/email/inbound.py`
- Create: `backend/app/calendar/__init__.py`
- Create: `backend/app/calendar/stub.py`

- [ ] Write failing agent-turn tests for initial outreach, negotiation, booking, and walk-away paths.
- [ ] Implement outbound email sending, IMAP thread matching, and calendar booking helpers.
- [ ] Implement the agent turn orchestration and verify the tests pass.
- [ ] Commit the end-to-end action layer.

### Task 5: Routing, Puter fallback, and scheduler

**Files:**
- Create: `backend/tests/test_reschedule_loop.py`
- Create: `backend/app/routers/threads.py`
- Create: `backend/app/routers/agent.py`
- Create: `backend/app/routers/email.py`

- [ ] Write the reschedule loop test for five cancellations.
- [ ] Implement thread CRUD, manual triggers, Puter processing, and email intake routes.
- [ ] Wire APScheduler into the app lifespan for IMAP polling.
- [ ] Commit the API completion slice.

### Task 6: Frontend dashboard

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/ThreadList.tsx`
- Create: `frontend/src/components/ThreadDetail.tsx`
- Create: `frontend/src/components/MessageBubble.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/PuterFallback.tsx`
- Create: `frontend/src/hooks/useAgentStatus.ts`
- Create: `frontend/src/types/index.ts`

- [ ] Scaffold the Vite React app with strict TypeScript and Tailwind.
- [ ] Implement the dashboard, thread creation form, and status bar.
- [ ] Implement the Puter.js fallback path through the shared API client only.
- [ ] Commit the frontend slice.

### Task 7: Infrastructure, samples, and docs

**Files:**
- Create: `backend/alembic/*`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml`
- Create: `samples/successful_booking.json`
- Create: `samples/reschedule_loop.json`
- Create: `samples/graceful_walkaway.json`
- Create: `README.md`

- [ ] Add the initial Alembic migration for threads, messages, and bookings.
- [ ] Add Docker builds for backend and frontend plus compose orchestration.
- [ ] Add sample transcripts and the complete root README.
- [ ] Run lint, tests, build, and commit the final documentation and infrastructure.
