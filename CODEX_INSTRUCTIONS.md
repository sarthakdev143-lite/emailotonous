# Codex Build Instructions — Strict Policies

These rules are **non-negotiable**. Every policy below must be followed exactly.
A senior engineer will review the repo, git history, code quality, and structure.

---

## 1. Git History Policy

- **Every logical unit of work = one commit.** Never batch unrelated changes.
- **Commit message format** — Conventional Commits, strictly:
  ```
  <type>(<scope>): <short description>

  [optional body — what and why, not how]
  ```
  Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `ci`
  Examples:
  ```
  feat(db): add Thread and Message SQLAlchemy models with async session
  feat(agent): implement intent classifier with keyword fallback
  feat(email): add IMAP poller with In-Reply-To thread matching
  feat(llm): implement OpenAI → Groq → LLMUnavailableError fallback chain
  feat(frontend): add PuterFallback component for zero-API-key mode
  fix(agent): prevent repeated slot proposals on same thread
  test(reschedule): add N-cancellation loop integration test
  docs: add architecture diagram and trade-offs to README
  ```
- **No "initial commit" with all code.** Build incrementally. Minimum expected commits: 25+
- **No commit message like** `wip`, `update`, `fix stuff`, `done`, `asdf`
- **Each commit must leave the codebase in a working state** (no broken imports, no syntax errors)

---

## 2. Project Structure Policy

- **Follow the folder structure in the prompt exactly.** Do not invent new top-level directories.
- Every Python module must have an `__init__.py`.
- `config.py` must use `pydantic-settings` `BaseSettings` — no `os.getenv()` scattered across files.
- All constants go in `config.py` — never inline magic strings or numbers elsewhere.
- The `agent/`, `email/`, `calendar/` directories are separate concerns — **no cross-imports** except through `app/` level imports.

---

## 3. Secrets and Environment Policy

- **`.env` must NEVER be committed.** It must be in `.gitignore` from commit #1.
- `config.example.env` must exist with every key listed, values blank or with placeholder comments.
- No API key, password, or secret may appear anywhere in code — not even in comments.
- `SECRET_KEY` must default to a generated value in dev but warn loudly if not set in production.

---

## 4. Code Quality Policy

### Python
- **Type hints on every function signature** — parameters and return types, no exceptions.
- **Docstrings on every class and public method** — one-line minimum.
- No bare `except:` — always catch specific exceptions.
- All async functions must be `async def` — no mixing sync blocking calls in async context.
- Use `logging` module — never `print()` in production code. `print()` only allowed in test scripts.
- All database operations must use the async session — no sync SQLAlchemy calls.
- SQLAlchemy models must use `mapped_column` and `Mapped` (SQLAlchemy 2.0 style).
- Format with `black`, lint with `ruff`. Both must pass with zero errors.

### TypeScript / React
- Strict TypeScript — `"strict": true` in `tsconfig.json`, no `any` types.
- No inline styles — Tailwind classes only.
- Every component must have a typed `Props` interface.
- API calls go through `api/client.ts` only — no `fetch` or `axios` calls directly in components.
- Handle loading and error states in every data-fetching component.

---

## 5. No Placeholder Code Policy

- **No `TODO`, `FIXME`, `pass`, or `raise NotImplementedError`** in any committed code.
- Every function must be fully implemented.
- The calendar stub is an exception — it must be clearly marked with a `# STUB:` comment at the top of the file explaining what the real implementation would use.
- The Puter.js path must be fully functional — not a stub.

---

## 6. Error Handling Policy

- Every external call (LLM API, Resend, IMAP) must have try/except with retry logic or graceful degradation.
- LLM failures must trigger the fallback chain — never crash the agent loop.
- IMAP polling errors must log and retry on next interval — never kill the poller.
- All FastAPI route handlers must return proper HTTP status codes:
  - `404` for missing threads
  - `422` for invalid input (Pydantic handles this automatically)
  - `503` if LLM unavailable and no Puter.js path available
- Never expose stack traces in API responses in production mode.

---

## 7. Agent Design Policy

- **The LLM must respond with a structured tool call only** — no free-text responses from the agent.
- The system prompt must be in `agent/prompts.py` as a function — not hardcoded in `core.py`.
- Full thread history must always be included in every LLM call — the agent has no selective memory.
- The agent must never send more than one email per turn.
- Thread `status` transitions must follow this state machine — no illegal transitions:
  ```
  pending → outreach_sent → negotiating → slot_proposed → booked
                                       ↘ closed_no_fit
  booked → slot_proposed (reschedule)
  outreach_sent → closed_no_reply
  ```
- The reschedule loop must work without degradation after N iterations (test with N=5).

---

## 8. Testing Policy

- Minimum 3 test files as specified in the prompt.
- Tests must use `pytest` + `pytest-asyncio`.
- Mock all external calls (LLM, Resend, IMAP) — tests must run offline.
- Tests must pass with `pytest -v` from the `backend/` directory with zero failures.
- No test file may be empty or contain only `pass`.

---

## 9. README Policy

The root `README.md` must be complete enough that a person who has never seen the repo can:
1. Clone it
2. Copy `config.example.env` to `.env`, fill in one set of credentials
3. Run `docker-compose up` OR follow manual setup steps
4. See the agent send a real email and respond to a reply

Required sections (in this order):
1. Project overview (2–3 sentences)
2. Architecture diagram (Mermaid or ASCII)
3. Tech stack table
4. Setup & run (step-by-step, including all three LLM modes)
5. How to trigger the reschedule loop demo
6. Sample transcript references
7. Trade-offs & known limitations
8. Swapping the calendar stub

---

## 10. Docker Policy

- `docker-compose.yml` must bring up the full stack (backend + frontend) with one command.
- Backend Dockerfile must use a multi-stage build.
- Frontend Dockerfile must serve the built React app via nginx.
- `docker-compose up` must work without any manual pre-steps beyond filling `.env`.

---

## 11. Dependencies Policy

- Pin all Python dependencies in `requirements.txt` with exact versions (`==`).
- Pin all npm dependencies — `package-lock.json` must be committed.
- No unused dependencies in either file.
- Required Python packages (minimum):
  ```
  fastapi==...
  uvicorn[standard]==...
  sqlalchemy[asyncio]==...
  aiosqlite==...
  alembic==...
  pydantic-settings==...
  openai==...
  groq==...
  resend==...
  apscheduler==...
  python-dotenv==...
  black==...
  ruff==...
  pytest==...
  pytest-asyncio==...
  httpx==...   # for FastAPI test client
  ```

---

## 12. What Will Be Reviewed

The senior engineer will specifically check:

| Check | What They Look For |
|---|---|
| Git log | Incremental, meaningful commits with proper messages |
| Secrets | `.env` absent from history, `config.example.env` present |
| Agent loop | Clean separation of perceive → reason → act |
| Reschedule | Works 5 times without degradation or context loss |
| LLM fallback | All three paths (OpenAI, Groq, Puter.js) reachable and functional |
| Error handling | No crashes on IMAP failure, LLM timeout, bad input |
| Type safety | No missing type hints, no `any` in TypeScript |
| Tests | All pass offline, cover intent + reschedule loop |
| README | Setup works first try |
| Code smell | No dead code, no magic strings, no print statements |
