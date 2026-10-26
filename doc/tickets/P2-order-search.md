# P2 – Order Search

**Labels:** `feature`, `api`, `database`
**Branch:** `feature/p2-order-search`
**Depends on:** P1
**Timebox:** 15 min

## Context

Temple staff look up orders all day at the counter. The order list can grow to **hundreds of thousands** of rows.

## User story

As **counter staff**, I can list a temple's orders filtered by date and status, and search by the devotee's phone number, page by page, so I can quickly find a devotee's booking.

## Requirements

1. List orders **for a temple**, with optional filters:
   - booking `date`
   - `status`
   - devotee `phone`
2. Results are **paginated** in a **stable order** (deterministic, no repeats or gaps between pages).
3. Introduce **database migrations** (e.g. Alembic) for the schema; the app no longer relies on `create_all`.
4. Add **indexes** so the common searches don't scan the whole table.

## Acceptance criteria

- [ ] Searching by phone number returns **only** that devotee's orders.
- [ ] Requesting page 2 returns the next set of results with **no repeats or gaps** from page 1.
- [ ] Filters combine (temple + date + status + phone).
- [ ] Invalid paging params (zero/negative size, size above max, malformed cursor) are rejected in the standard error format.
- [ ] Migrations build the full schema from an empty DB (`alembic upgrade head`).
- [ ] The PR shows the common searches use indexes (e.g. `EXPLAIN QUERY PLAN` output).

## Decisions to make (record in PR "Assumptions")

- **Pagination style**: offset/limit vs. keyset (cursor). Keyset on `(created_at, id)` or `id` scales better and isn't affected by new inserts shifting pages; offset is simpler. Document the trade-off.
- **Sort order**: e.g. newest first with `id` as tie-breaker.
- **Phone match**: exact match on the normalised phone vs. prefix/partial.
- **Index design**: e.g. composite `(temple_id, booking_date, status, id)` and `(temple_id, phone, id)`; justify column order.
- **Default and max page size.**
- **Response envelope**: items + `next_cursor`, or `page`/`size`/`total`? (`COUNT(*)` on a large table is costly.)
- **Migrations vs. tests**: tests may keep `create_all` on in-memory SQLite or run migrations; note which and why. Update `CLAUDE.md`/README, which currently say "no migrations".

## Definition of done

- [ ] PR uses the assessment template, including Assumptions.
- [ ] At least one line-level review comment left and addressed before merge.
- [ ] Tests, ruff, mypy green; README documents the migration command.
