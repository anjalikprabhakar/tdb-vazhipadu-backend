---
name: contract-change
description: >-
  The contract-first workflow for this service's interface: the HTTP API (paths, Pydantic request and
  response schemas, status codes, the shared error shape) and the database schema (models and Alembic
  migrations). Decide the shape from the ticket, classify the change as additive or breaking, write
  the migration and contract tests before the service logic, and record a migration note when it
  breaks. Use whenever a ticket or request adds, removes or reshapes an endpoint, a request or
  response field, a status code, an enum value, a table, a column or an index (e.g. P2's search
  endpoint and migrations, P3's daily_limit, P4's CANCELLED status and report), even if the user never
  typed the command. Invoke as /contract-change.
---

# Contract change

This service has no separate contract file. Its contract is the code that publishes it:

- **API**: the routes in `api/`, the Pydantic schemas in `schemas/`, their status codes and the one
  shared JSON error shape. FastAPI renders all of it as `/openapi.json`, which is what a client reads.
- **Database**: the models in `models/` and, from P2 on, the Alembic migrations that build them.

The contract holds only if it moves first. A route that returns a field no schema declares, or a
model column no migration creates, is a defect the next reader finds as a confusing failure rather
than as a clear statement of the interface.

## Why contract first

One problem is one branch and one PR here, so the contract does not get its own PR. Instead it gets
its own **first commits** on the problem's branch: schemas, models and migration, plus the tests
that pin them, before any service logic. That forces the shape to be decided once, from the ticket,
and written down in the PR's Assumptions, rather than drifting while the logic is written.

## Steps

### 1. Decide the shape

Read the ticket in `doc/tickets/`, its "Decisions to make", and the `python-conventions` skill
(its data/API and domain rules are binding here). The contract describes the interface, not the
storage:

- `*Read` schemas expose what a client may rely on, not every column. Internal columns (a normalised
  phone used for search, a counter table for daily limits) stay out unless the ticket asks for them.
- Money keeps the representation P1 chose (`Decimal` or integer paise) in every new field. Never a
  `float`, and never a second representation beside the first.
- Every new failure uses the shared error shape and a status code chosen deliberately (e.g. 409 vs
  422 for "limit exceeded"). Write the choice down.
- A field that can be absent or `null` says so in its type (`daily_limit: int | None`) and in the
  PR, with what `null` means ("unlimited"). A client that assumes it is always present builds a
  workaround that hides the defect.

Every choice the ticket leaves open goes into the PR's **Assumptions**.

### 2. Classify the change

Compare the published contract before and after (step 4) and classify each difference:

| Change | Class | Extra |
|---|---|---|
| New endpoint; new optional request field; new response field; new nullable column, table or index | **additive** | none |
| Removing or renaming a field, endpoint or column; making an optional field required; adding a `NOT NULL` column with no server default; narrowing a type or enum; changing a status code, the error shape or the meaning of a field | **breaking** | a migration note in the PR |
| New enum value (e.g. `CANCELLED`) | **additive for the API, check the database** | if the enum is a `CHECK` constraint, the migration must rebuild it |

When unsure whether a change is additive, assume it breaks. The service has no version number to
bump; the PR is the version boundary, so a breaking change is recorded there instead.

A **migration note** goes under **Decisions & trade-offs**: what breaks, for whom (API clients,
existing rows in `app.db`), and what they do about it (e.g. "existing orders backfilled to
`CONFIRMED`", "delete local `app.db` before P2").

### 3. Make the change, contract first

Commit in this order, each a small Conventional Commit:

1. **Schemas and models**: the Pydantic schemas with `Field` constraints that mirror the column
   limits, and the SQLAlchemy model changes, registered in `models/__init__.py`.
2. **Migration** (from P2 on): `uv run alembic revision --autogenerate -m "<what changed>"`, then
   read it before committing. Autogenerate misses or gets wrong:
   - enum value changes and `CHECK` constraints;
   - server defaults and backfills for a new `NOT NULL` column on existing rows;
   - index names and column order (match the ticket's search paths, e.g. `(temple_id, booking_date,
     status, id)`).
   SQLite cannot alter most columns in place, so `env.py` uses `render_as_batch=True` and column
   changes go through `op.batch_alter_table`. A migration that is already on `main` is never edited;
   write a new one.
3. **Contract tests**: through the `client` fixture, assert the status code, the exact response keys
   and types that matter, and the shared error shape for each new failure.
4. **Service logic** in `services/`, then the router that calls it.

### 4. Check the contract

```bash
# The published API, before and after (run once on origin/main, once on the branch)
uv run python -c "import json; from assessment.main import app; print(json.dumps(app.openapi(), indent=2, sort_keys=True))" > <scratchpad>/openapi-<ref>.json
git diff --no-index <scratchpad>/openapi-main.json <scratchpad>/openapi-branch.json

# From P2 on: the migrations build the schema from empty, round-trip, and match the models
APP_DATABASE_URL=sqlite+aiosqlite:///<scratchpad>/contract.db uv run alembic upgrade head
APP_DATABASE_URL=sqlite+aiosqlite:///<scratchpad>/contract.db uv run alembic downgrade -1
APP_DATABASE_URL=sqlite+aiosqlite:///<scratchpad>/contract.db uv run alembic upgrade head
APP_DATABASE_URL=sqlite+aiosqlite:///<scratchpad>/contract.db uv run alembic check
```

Every difference in the OpenAPI diff is one you intended and classified in step 2; an unexpected one
is a defect. `alembic check` failing means a model changed with no migration. Before P2 there are no
migrations: say in the PR that the local `app.db` must be deleted.

### 5. Then the rest of the ticket

If the implementation shows the contract is wrong, **go back and change the contract**: the schema,
the migration and its tests, and the PR's Assumptions. Do not adapt around it in code. A route that
returns something its schema does not declare has a defect, and a test loosened to accept it hides
that defect from the reviewer.

## Quality gates

| Gate | Command |
|---|---|
| Gate Commands | the `quality-check` skill (registered in `CLAUDE.md` under `## Project-specific`) |
| Contract diff reviewed | the OpenAPI before/after diff in step 4, every difference classified |
| Migrations build from empty (P2 on) | `uv run alembic upgrade head` on an empty database |
| Migrations round-trip (P2 on) | `uv run alembic downgrade -1` then `uv run alembic upgrade head` |
| Models match migrations (P2 on) | `uv run alembic check` |
