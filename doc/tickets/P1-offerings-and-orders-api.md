# P1 – Offerings and Orders API

**Labels:** `feature`, `api`
**Branch:** `feature/p1-offerings-orders`
**Timebox:** 20 min

## Context

Devotees book offerings (vazhipadu) such as Pushpanjali or Archana at a temple, for a chosen date. A devotee pays a fixed fee per offering; the priest performs the ritual, usually in the name of a person and their birth star.

## User stories

- As **temple staff**, I can manage a temple's offerings (name, price, active flag) so devotees can only book what the temple performs.
- As a **devotee**, I can place an order for one or more offerings, each with a quantity, for a date, so the ritual is performed in my name.
- As **staff or a devotee**, I can fetch an order by id to see what was booked and the total.

## Requirements

1. Manage offerings: `name`, `price`, `is_active`.
2. Create an order with:
   - devotee `name`, `phone`, `nakshatra` (birth star)
   - booking `date`
   - one or more line items: `offering_id` + `quantity`
3. The **server** computes the order total; client-supplied prices/totals are never trusted. Line items snapshot the unit price at order time.
4. `GET` an order by id (including line items and total).
5. Invalid input is rejected with a clear error, using **one consistent JSON error format for all errors** (validation, not found, business-rule violations, unexpected errors).

## Acceptance criteria

- [ ] An order for **2 × Pushpanjali @ ₹30** and **1 × Archana @ ₹50** has total **₹110**.
- [ ] An order containing an **inactive** offering is rejected with the standard error format.
- [ ] Unknown offering id, empty item list, quantity ≤ 0, missing/invalid phone, invalid nakshatra are rejected with the standard error format.
- [ ] `GET /orders/{id}` returns 404 in the standard error format for an unknown id.
- [ ] At least one automated test (aim: one per criterion above).

## Decisions to make (record in PR "Assumptions")

- **Temple modelling**: P2 and P4 query "for a temple". Introduce a `Temple` entity now, or just a `temple_id`? (Suggested: minimal `Temple` table; offerings belong to a temple; all offerings in one order must belong to the same temple.)
- **Money type**: integer paise or `Decimal(10,2)`; never `float` (P4 requires paisa-exact totals).
- **Nakshatra**: free text vs. enum of the 27 nakshatras (suggested: enum).
- **Phone**: format rules (e.g. Indian 10-digit, optional `+91`) and normalisation before storage (matters for P2 search).
- **Booking date**: may it be in the past? (Suggested: reject past dates, evaluated in IST.)
- **Same offering twice in one order**: merge or reject?
- **Order status**: add `status` (e.g. `CONFIRMED`) now so the P2 filter and P4 cancel fit naturally.
- **Offering deletion**: deactivate only, since orders reference offerings.
- **Error format**: e.g. `{"error": {"code": "...", "message": "...", "details": [...]}}`, applied via exception handlers for `HTTPException`, `RequestValidationError` and domain errors.

## Definition of done

- [ ] PR uses the assessment template, including Assumptions.
- [ ] At least one line-level review comment left and addressed before merge.
- [ ] Tests, ruff, mypy green.
