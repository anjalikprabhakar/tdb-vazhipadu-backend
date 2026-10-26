# P4 – Cancellation and Daily Collection

**Labels:** `feature`, `reporting`
**Branch:** `feature/p4-cancellation-collection`
**Depends on:** P1, P3
**Timebox:** 15 min

## Context

Staff need to cancel orders, and Finance reconciles a daily collection report against their books, so totals must match **to the paisa**. Days are counted in **Indian Standard Time (IST, UTC+05:30)**.

## User stories

- As **staff**, I can cancel an order so its slots are released for other devotees.
- As **Finance**, I can get the daily collection for a temple and date (total amount and count per offering) and reconcile it exactly with our books.

## Requirements

1. Cancel an order (status becomes `CANCELLED`). A cancelled order **frees its daily limit**.
2. Daily collection report for a **temple + date**:
   - per offering: offering, count (quantity), amount
   - overall total amount
3. Amounts are exact to the paisa (no floating point).
4. Days are bucketed in IST.

## Acceptance criteria

- [ ] A cancelled order is **not counted** in the report, and its daily limit **becomes available** again.
- [ ] An order placed at **00:15 IST** on a date is counted **on that date** (that is 18:45 UTC the previous day).
- [ ] The report total **equals the sum of its offerings' totals**.
- [ ] Cancelling an unknown order returns 404; cancelling an already-cancelled order is handled per the decision below, in the standard error format.
- [ ] Amounts are serialised without float rounding (e.g. `"110.00"` as a string, or integer paise).

## Decisions to make (record in PR "Assumptions")

- **Which date the report uses**: booking (ritual) date vs. the date the order was placed/paid (`created_at` in IST). "Collection" and the 00:15 IST criterion point to the **placement date in IST**; state the choice clearly.
- **Timestamp storage**: store timezone-aware UTC and convert to IST when bucketing, or store an IST `collection_date` column at insert time (simpler, indexable, avoids SQLite timezone functions).
- **Cancel semantics**: idempotent (200 on repeat) vs. 409; can orders for past dates be cancelled? Refunds out of scope?
- **Endpoint shape**: `POST /orders/{id}/cancel` vs. `PATCH` on status.
- **Concurrency**: release the P3 daily usage in the same transaction as the status change.
- **Report contents**: include offerings with zero orders? Use the price snapshot on order lines, not the current offering price.

## Definition of done

- [ ] PR uses the assessment template, including Assumptions.
- [ ] At least one line-level review comment left and addressed before merge.
- [ ] README links all 4 PRs; all tests, ruff, mypy green.
