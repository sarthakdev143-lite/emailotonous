# Backend Service

This backend owns thread persistence, agent orchestration, IMAP polling, outbound email delivery, and the Puter.js execution path. It runs as an async FastAPI service on Python 3.11.

## Local commands

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test commands

```bash
pytest -v
ruff check .
black --check .
```

## Important modules

- `app/agent/core.py`: full perceive → reason → act loop
- `app/agent/intent.py`: intent classification with server-side LLM and keyword fallback
- `app/email/inbound.py`: IMAP polling and thread matching
- `app/email/outbound.py`: Resend delivery adapter
- `app/calendar/stub.py`: mock booking provider
- `app/routers/*`: API routes used by the React dashboard
