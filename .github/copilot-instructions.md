# Copilot instructions — MyPlan (StudyPlan)

## Project

MyPlan is our version of the StudyPlan assignment: a student imports courses (PDF or Markdown), MyPlan derives chapters and workload in hours, builds a weekly study plan in the student's free slots, exports it as `.ics` and tracks progress on a dashboard. **The product makes no call to any AI API.** The specification is in `SPEC.md` (French): read it before any change. Design documents are in `docs/`.

## API contract (frozen: extend it, never break it)

```
POST   /courses              multipart file -> {id, name, chapters:[{id,title,hours}], hours_total}
GET    /courses              -> [{id, name, hours_total, hours_done, progress}]
POST   /deadlines            {course_id, title, type, date, weight} -> 201
GET    /deadlines            -> list sorted by date
DELETE /deadlines/{id}       -> 204
PUT    /availability         {session_minutes, slots:{monday:["18:00-20:00"], ...}}
POST   /plan/generate        {week: "2026-W47"} -> [{id, course_id, chapter_id, start, end, done}]
GET    /plan?week=2026-W47   -> sessions of the week
PATCH  /sessions/{id}        {done: true}
GET    /plan.ics             -> text/calendar
```

- No path prefix. Every route above requires `Authorization: Bearer <token>` (FastAPI dependency `CurrentUser` in `backend/api/deps.py`).
- `type` is `exam` or `assignment`; `weight` is 0 to 100; a date in the past returns 422.
- Errors always have the shape `{"error": {"code": "...", "message": "...", "details": {...}}}`, message in French.
- Extensions already in place: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `GET|PATCH|DELETE /courses/{id}`, `GET|PATCH /settings`.

## Stack

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic on SQLite, Streamlit, pytest, ruff.
- `pypdf` for PDF text, `markdown-it-py` for Markdown, `icalendar` for `.ics`.
- Do not add a new dependency without asking first and explaining why. **Never add an AI or LLM library.**

## Code style

- Identifiers in English; file headers, docstrings and comments in **French** (`docs/conventions_de_nommage.md` §12).
- Type hints everywhere, small functions, explicit names, Google-style docstrings on public functions.
- Pure domain code in `backend/domain/`: no database, no network, no clock (`now` is a parameter).
- Every repository method takes `user_id` as first argument; another user's resource returns 404.
- Datetimes are timezone-aware UTC (`UtcDateTime` column type rejects naive ones); weekly availability is stored in local time (`LocalTime`).
- API responses go through a `...Read` Pydantic schema, never a SQLAlchemy model. Incoming text uses the types in `backend/api/schemas/common.py`.
- Streamlit pages live in `frontend/views/`, **never** in `frontend/pages/` (Streamlit would run them without the login check). Use `frontend/components/ui.py`; display user or imported text with `escape_markdown`; never render raw HTML.
- No secrets in code: read them from environment variables (`backend/core/config.py`; `.env` is git-ignored).
- SQL only through SQLAlchemy, never string-built queries.

## Workflow

- Before coding a feature, propose a short plan and wait for approval.
- Work in small steps. After each change, run `pytest -q` and `ruff check .`, and fix failures before continuing.
- Never delete or weaken an existing test to make it pass.
- Alembic `--autogenerate` output must be read and tested on a non-empty database before committing.
- When unsure about an API or library behaviour, say so instead of guessing.

## Answers

- Explain what you changed and why in 3 bullet points max.
