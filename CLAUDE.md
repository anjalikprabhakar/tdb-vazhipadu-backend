# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Uses `uv` (Python 3.11+). Run everything through `uv run`.

```bash
uv sync                                   # install deps into .venv
uv run assessment                         # run API (uvicorn; reload when APP_DEBUG=true)
uv run uvicorn assessment.main:app --reload

uv run pytest                             # all tests
uv run pytest tests/test_api.py::test_health   # single test
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests                     # strict mode, pydantic plugin
```

API docs at http://127.0.0.1:8000/docs.

## Architecture

FastAPI + async SQLAlchemy 2 (aiosqlite) in a `src/` layout package `assessment`. `Item` is a placeholder resource meant to be replaced by the assessment's real domain.

Request flow: router in `api/` → `SessionDep` (`api/deps.py`, wraps `db.get_session`) → SQLAlchemy model in `models/` → returned via a Pydantic schema in `schemas/` (`*Read` schemas use `from_attributes=True` so endpoints return ORM objects directly with `response_model`).

Wiring that spans files when adding a resource:
- **Models must be imported in `models/__init__.py`.** `main.py` does `from assessment import models` purely to register tables on `Base.metadata`; an unimported model gets no table.
- **Routers must be registered** with `app.include_router(...)` in `main.py`.
- **Migrations:** until P2, tables are created with `Base.metadata.create_all` in the app lifespan and schema changes to existing tables require deleting the local `app.db`. From P2 on (required by the brief), every schema change needs an Alembic migration.

Config: `config.py` exposes a module-level `settings` (pydantic-settings, `APP_` env prefix, reads `.env`). The engine in `db.py` is built from it at import time.

## Tests

pytest-asyncio with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed). The `client` fixture in `tests/conftest.py` creates a fresh in-memory SQLite engine per test, runs `create_all` itself (httpx `ASGITransport` does not run the app lifespan), and overrides `get_session` via `app.dependency_overrides`.

## Workflow (skills in `.claude/skills/`)

Assessment brief: `doc/Backend_SE_GRADE_II.pdf`; tickets P0–P4 in `doc/tickets/`. One branch → PR → review → merge per problem, in order; never commit to `main` after setup.

Ticket → PR flow: `/implement-ticket <P1|#issue>` → `/review-ticket <ticket>` → `/raise-pr` → `/review-pr <n> --post` (at least one line comment) → `/address-pr-feedback <n>` → `/merge-pr <n>`.
Helpers: `/quality-check` (all four gates), `/add-resource <Name> field:type ...` (model/schema/router/tests scaffold), `/fix-review-comments <n>` (verify and fix the latest `/review-pr` findings, reply, push).
`code-reviewer` agent (`.claude/agents/`) gives an independent read-only review; used by the review skills.
PR body follows `.github/pull_request_template.md` (Problem / Assumptions / Decisions & trade-offs / How to test; Assumptions is mandatory). Branches: `feature/p<N>-<slug>` / `fix/...`; small, meaningful Conventional Commits (never `fix`, `wip`, `changes`, `final`). The README links every PR.
A PostToolUse hook (`.claude/hooks/format_python.py`) runs `ruff format` + `ruff check --fix` on every edited `.py` file and surfaces unfixable lint errors.

## Project-specific

- **Stack**: Python (FastAPI, async SQLAlchemy 2, Pydantic v2, SQLite via aiosqlite).
- **Package Manager**: `uv` (`uv sync`, `uv add`, `uv run`).
- **Gate Commands**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src tests`.
- **Standard**: `.claude/skills/python-conventions/SKILL.md` is the bar for all Python changes.

## Conventions

- mypy `strict = true`: all functions (including tests) need full type annotations.
- Ruff: line length 100, rules `E, F, I, UP, B, ASYNC`.
