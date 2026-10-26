# P3 – Daily Limits

**Labels:** `feature`, `concurrency`
**Branch:** `feature/p3-daily-limits`
**Depends on:** P1, P2 (migrations)
**Timebox:** 15 min

## Context

Some offerings can only be performed a fixed number of times a day, e.g. **50 Udayasthamana Poojas**. Online and counter orders are placed at the same time, so the limit must hold under simultaneous requests.

## User story

As the **temple board**, I can set an optional daily limit on an offering so it is never over-booked for a date, however many orders arrive at once.

## Requirements

1. Offerings have an optional `daily_limit` (null = unlimited), added via a migration.
2. An order is rejected if it would take any of its offerings **over the daily limit for that booking date** (sum of quantities across non-cancelled orders).
3. The check is **race-free** under concurrent requests (no check-then-insert race).

## Acceptance criteria

- [ ] Daily limit 5 with 4 already booked: an order for **2 is rejected**, an order for **1 succeeds**.
- [ ] An automated test fires **20 simultaneous orders for 1 each** against a daily limit of 5: **exactly 5 succeed**, the other 15 are rejected with the standard error format.
- [ ] Multi-item orders are all-or-nothing: if one item exceeds its limit, nothing is booked.
- [ ] Offerings without a limit are unaffected.

## Decisions to make (record in PR "Assumptions")

- **Concurrency strategy**, for example:
  - a counter table `offering_daily_usage(offering_id, date, booked)` updated with an atomic conditional `UPDATE ... SET booked = booked + :q WHERE booked + :q <= :limit` (works on SQLite and PostgreSQL);
  - `SELECT ... FOR UPDATE` row lock (PostgreSQL only; SQLite has no row locks);
  - SQLite `BEGIN IMMEDIATE` / serialised writes.
  Justify the choice and its portability.
- **SQLite test setup**: the concurrent test needs a file-based DB (or shared connection) with a busy timeout / WAL. A single in-memory `StaticPool` connection may serialise everything and hide the race; make sure the test would fail without the fix.
- **Lowering a limit below current bookings**: allowed (only blocks new orders) or rejected?
- **Status code**: 409 Conflict vs. 422 for "limit exceeded"; include remaining capacity in the error details?
- **Multi-item orders**: lock/update rows in a consistent order (e.g. by `offering_id`) to avoid deadlocks.

## Definition of done

- [ ] PR uses the assessment template, including Assumptions.
- [ ] At least one line-level review comment left and addressed before merge.
- [ ] Concurrency test is deterministic (run it several times) and green; ruff, mypy green.
