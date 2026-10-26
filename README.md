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
uv run alembic upgrade head   # create or upgrade the database schema (required before first run)
uv run assessment             # or: uv run uvicorn assessment.main:app --reload
```

- API docs (Swagger UI): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Configuration uses `APP_*` environment variables or `.env`. The database defaults to `sqlite+aiosqlite:///./app.db`.

### Database migrations

The schema is managed by Alembic (`migrations/`). The app does not create tables itself.

```bash
uv run alembic upgrade head                              # apply all migrations
uv run alembic revision --autogenerate -m "<change>"     # after changing a model; review the file
uv run alembic check                                     # fails if models and migrations differ
```

A local `app.db` created before migrations existed (P1) must be deleted once.

## Run the tests

```bash
uv run pytest                                  # all tests
uv run pytest tests/test_api.py::test_health   # a single test
```

Tests use a fresh in-memory SQLite database per test (built with `create_all` for speed), so no setup is needed. `tests/test_schema.py` separately migrates an empty database, round-trips the migrations, runs `alembic check` and asserts the order searches use indexes.

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
  services/      business rules (pricing, daily limits, cancellation, reports)
migrations/      Alembic migrations
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
| P2 – Order Search | [#10](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/10) |
| P3 – Daily Limits | [#11](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/11) |
| P4 – Cancellation and Daily Collection | [#12](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/12) |

## Walkthrough

A summary of the decisions taken for each problem and the places where the AI's work was corrected. Each PR's **Assumptions** and **Decisions & trade-offs** sections have the full list and the reasoning.

### Cross-cutting decisions

- **Money is integer paise.** A custom `Money` column stores integer paise and exposes `Decimal`. The API sends amounts as strings (`"110.00"`). SQLite has no exact decimal type: `Numeric` is stored as REAL, so a `SUM` would add floats and could drift by a paisa. That matters most for P4's report.
- **Time is UTC in the database, IST for business days.** A `UtcDateTime` column rejects naive datetimes. Business days (booking dates, report days) are IST, from `ZoneInfo("Asia/Kolkata")`.
- **One error format.** Every error, including framework 404/405, malformed JSON and unexpected 500s, is `{"error": {"code", "message", "details"}}`, produced only by the handlers in `errors.py`.
- **Status codes:**
  - 422 when the request content is invalid, including an unknown or inactive offering in the body.
  - 404 only when the resource in the URL doesn't exist.
  - 409 when a valid request conflicts with current state: a duplicate name, a daily limit reached, an order already cancelled or no longer cancellable.
- **Layering.** Routers only handle HTTP. Business rules live in `services/`.
- **Contract first.** From P2 on, each PR commits schemas, models and migration before the logic, checks the OpenAPI diff, and runs `alembic check`. Every change to the API so far has been additive.

### P1 – Offerings and Orders API ([#9](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/9))

- **Temples.** A minimal `Temple` resource was added up front because later problems query "for a temple". An offering from another temple is treated as unknown.
- **Price snapshot.** Each line item stores the unit price at order time, so a later price change never alters an existing order or a past report.
- **Input normalisation:**
  - Phone numbers are normalised to 10 digits (`+91`, a leading `0`, spaces and hyphens are stripped).
  - Nakshatra must be one of the 27 Sanskrit names; input is case-insensitive.
  - The booking date must be today or later in IST.
- **Order rules.** The same offering twice in one order is rejected rather than merged. Quantity is 1 to 100 per line.
- **No hard deletes.** Offerings are deactivated, because orders reference them.

### P2 – Order Search ([#10](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/10))

- **Pagination.** Keyset pagination (`id < cursor ORDER BY id DESC`) rather than offset, so pages never repeat or skip when orders arrive between requests. The trade-off is no "jump to page N" and no total count.
- **Cursor.** An opaque, strictly validated cursor. Unknown query parameters return 422 rather than being ignored.
- **Indexes.** Four indexes: `(temple_id, id)`, `(temple_id, booking_date, id)`, `(temple_id, status, id)`, `(temple_id, phone, id)`. Query plans showed the ticket's example indexes needed a temporary sort for three common searches. `tests/test_schema.py` asserts every search uses an index without sorting.
- **Migrations.** Alembic took over the schema; the app no longer calls `create_all`.

### P3 – Daily Limits ([#11](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/11))

- **The limit.** An optional `daily_limit`; `null` means unlimited. An order over the limit gets 409 `daily_limit_exceeded`, listing the remaining capacity for each offering that didn't fit.
- **Atomic booking.** A counter table, `offering_daily_usage`, is updated with a conditional `UPDATE … WHERE booked + :q <= daily_limit` in the same transaction as the order. A whole order is accepted or rejected together.
  - Not chosen: a `SUM()` check followed by an insert, because that is the race the ticket describes; and `SELECT … FOR UPDATE`, because SQLite doesn't support it.
- **SQLite write transactions.** Every write service starts its transaction with `BEGIN IMMEDIATE`, so concurrent writers wait for each other instead of failing with `database is locked`.
- **Lowering a limit.** A limit can be lowered below current bookings. Existing orders stay; new ones are rejected until there is room.

### P4 – Cancellation and Daily Collection ([#12](https://github.com/anjalikprabhakar/tdb-vazhipadu-backend/pull/12))

- **Report date.** The report uses the date the order was placed (`created_at` in IST), not the ritual date. So an order at 00:15 IST counts on that day.
- **Day bucketing.** The IST day is converted to a UTC `created_at` range, backed by a `(temple_id, created_at)` index. This was chosen over a stored `collection_date` column, which would duplicate data and need a backfill.
- **Cancel endpoint.** `POST /orders/{id}/cancel`, chosen over `PATCH` on `status`.
  - Cancelling twice returns 409 `order_already_cancelled`.
  - Once the booking date has passed in IST, cancelling returns 409 `order_not_cancellable`.
  - Cancelling changes the status only; refunds are out of scope.
- **Releasing the limit.** The status change is a conditional `UPDATE … WHERE status='CONFIRMED'`. The daily-limit release happens in the same transaction, so capacity is never released twice.
- **Report contents:**
  - It uses the price recorded on each order line and sums integer paise in SQL.
  - The total is the sum of the returned lines, so it always reconciles.
  - Offerings with no orders that day are left out.
- **Accepted trade-off.** Cancelling an order removes it from the report for the day it was placed, even if Finance already reconciled that day. A `cancelled_at` column with an adjustments section is the additive follow-up if reconciled days must stay fixed.

### Where the AI was corrected

The code was written with Claude Code. Every PR also had an independent AI review, read in full before merging. These corrections are recorded in the PRs and their review threads:

| PR | Correction |
| -- | ---------- |
| #9 | The pre-PR review found three issues, all fixed before the PR opened. Renaming an offering to an existing name returned 500 instead of 409. The phone check accepted non-ASCII digits. A missing phone had no test. |
| #10 | Malformed cursors were mishandled. A deeply nested cursor caused a `RecursionError` (500), and invalid base64 was silently accepted as a valid id. Fixed in 1716d53 with strict decoding. |
| #11 | `BEGIN IMMEDIATE` was first applied only to `place_order`, so offering writes during orders returned 500. Fixed in 939bf02 by applying it to every write service. |
| #11 | `{"daily_limit": true}` was stored as a limit of 1, and `"5"` and `5.0` were accepted. Fixed in 74a93a3 with strict integer parsing. |
| #11 | The PR description claimed a naive check-then-insert over-books under the test. Measuring showed `BEGIN IMMEDIATE` alone serialises it on SQLite, so the description was corrected. |
| #12 | The AI recommended waiting for P3 to merge before starting P4. I started P4 from the P3 branch instead and fast-forwarded it onto `main` after #11 merged. |
| #12 | For the review question on whether late cancellations may change a reconciled day's total, I chose to keep the behaviour and document it, rather than add `cancelled_at` within the timebox. |

Review questions that were answered without a code change: integer paise versus `Numeric` (#9), and making the SQLite busy timeout configurable or mapping it to a 503 (#11, left as a follow-up). The reasons are in the threads.
