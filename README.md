# tdb-vazhipadu-backend

A small **vazhipadu (temple offering) booking service** for a temple board.

A vazhipadu is a ritual offering that a devotee pays the temple to perform. The devotee pays a fixed fee, and the priest performs the ritual, usually in the name of a person and their birth star (nakshatra).

Python 3.11+ · FastAPI · SQLAlchemy 2 (async) · SQLite (aiosqlite) · uv

## Features

| Problem | Scope |
| ------- | ----- |
| P1 – Offerings and Orders API | Manage a temple's offerings (name, price, active flag); place an order for one or more offerings for a date; the server calculates the total; get an order by id; one consistent JSON error format |
| P2 – Order Search | List a temple's orders filtered by date, status and phone number; stable pagination; database migrations and indexes |
| P3 – Daily Limits | Optional daily limit per offering that holds under simultaneous orders |
| P4 – Cancellation and Daily Collection | Cancel orders (frees the daily limit); daily collection report per temple and date, exact to the paisa, with days counted in IST |

The detailed tickets are in [`doc/tickets/`](doc/tickets/), and the original brief is [`doc/Backend_SE_GRADE_II.pdf`](doc/Backend_SE_GRADE_II.pdf).

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                    # create .venv and install deps
cp .env.example .env       # optional: APP_DEBUG, APP_DATABASE_URL
```

## Run the app

```bash
uv run assessment          # or: uv run uvicorn assessment.main:app --reload
```

- API docs (Swagger UI): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Configuration uses `APP_*` environment variables or `.env`. The database defaults to `sqlite+aiosqlite:///./app.db`.

## Run the tests

```bash
uv run pytest                                  # all tests
uv run pytest tests/test_api.py::test_health   # a single test
```

Tests use a fresh in-memory SQLite database per test, so no setup is needed.

## Quality checks

```bash
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run mypy src tests                                 # strict type checking
```

## Project layout

```
src/assessment/
  main.py        FastAPI app + lifespan
  config.py      pydantic-settings (APP_* env vars / .env)
  db.py          async engine, session factory, declarative Base
  api/           routers + dependencies
  models/        SQLAlchemy ORM models
  schemas/       Pydantic request/response models
tests/           pytest-asyncio + httpx ASGI client, in-memory SQLite
doc/             assessment brief and tickets (P0–P4)
```

## Development workflow

Each problem is one branch, one PR, one review and one merge, in order (P1 → P4). Nothing is committed directly to `main` after the initial setup.

1. Branch from the latest `main`: `feature/p<N>-<slug>` (e.g. `feature/p1-offerings-orders`).
2. Commit in small, meaningful steps (e.g. `feat(orders): compute order total on server`).
3. Open a PR into `main` using the [PR template](.github/pull_request_template.md): Problem, Assumptions, Decisions & trade-offs, How to test.
4. Review the full diff, leave at least one line comment, and address it with a commit or a reply.
5. Merge (squash or merge commit), then `git checkout main && git pull` before the next problem.

## Pull requests

| Problem | PR |
| ------- | -- |
| P1 – Offerings and Orders API | [#9](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/9) |
| P2 – Order Search | _TBD_ |
| P3 – Daily Limits | _TBD_ |
| P4 – Cancellation and Daily Collection | _TBD_ |
