---
name: implement-ticket
description: Implement a ticket end to end in this repo — branch, plan, code, tests, quality gates. Use when the user gives a ticket (pasted text, GitHub issue number, ticket file or problem ID like P1) and asks to implement/build/do it.
argument-hint: "<ticket text | #issue-number | P1..P4 | doc/tickets/<file>.md>"
---

# Implement ticket

Ticket: $ARGUMENTS

Context: this is the vazhipadu booking assessment (`doc/Backend_SE_GRADE_II.pdf`). Each problem is **one branch → one PR → one review → one merge, in order (P1 to P4)**. Problems are timeboxed (P1 20 min, P2–P4 15 min each), so keep scope tight.

## 1. Understand the ticket

- GitHub issue number (`#12` or `12`): `gh issue view <n>`. Problem ID (`P1`) or path: read the matching file in `doc/tickets/`. Otherwise treat the argument as the ticket text. If nothing was given, ask for the ticket.
- Extract: goal, **acceptance criteria** (as a numbered list), affected endpoints/models, out-of-scope items, and the ticket's **Decisions to make** list.
- The brief leaves details open on purpose, and **every assumption must be written down for the PR**. For each open decision, pick a sensible default and record it. Ask the user only when the choice changes the design substantially (e.g. pagination style, concurrency strategy, which date the report uses).

## 2. Branch

- `git status` must be clean of unrelated changes; if not, ask the user.
- Start from the **latest** `main`: `git checkout main && git pull`. Never commit directly to `main`.
- Branch name: the ticket's **Branch:** line if it has one, else `feature/p<N>-<short-slug>` (e.g. `feature/p1-offerings`), or `fix/...` for bugs.
- Don't start P(N+1) until P(N)'s PR is merged and `main` has been pulled.

## 3. Plan

State a short plan: files to add/change, endpoints with method/path/status codes, schema fields, migrations, test cases mapped to acceptance criteria. Keep it in chat; don't create plan files.

## 4. Implement

Load the `python-conventions` skill first; it is the standard every added or modified line is held to.
If the ticket adds or reshapes an endpoint, a schema field, a status code, a table, a column or an index, follow the `contract-change` skill: its schema, migration and contract-test commits come before the service logic.

Follow the existing patterns (`Offering` is the reference resource: model, schemas, service, router, tests). For each new resource, use the `add-resource` skill's checklist. Key rules from `CLAUDE.md` and the brief:

- Models in `models/`, **re-exported from `models/__init__.py`**.
- Schemas in `schemas/`: `<Name>Create`, optional `<Name>Update` (all fields optional, use `model_dump(exclude_unset=True)`), `<Name>Read` with `from_attributes=True`. Mirror column limits in `Field(...)`.
- Routers in `api/`, using `SessionDep`, **registered in `main.py`**.
- Status codes: 201 create, 204 delete, 404 missing, 409 conflicts / business-rule violations (catch `IntegrityError`, rollback).
- **One consistent JSON error format for all errors**: raise through the app's shared error handlers; never return ad-hoc error shapes.
- **Money**: `Numeric`/`Decimal` or integer paise; never `float`. Totals are always computed on the server.
- **Dates/times**: days are counted in IST (`Asia/Kolkata`); store timezone-aware timestamps.
- **Schema changes**: once Alembic exists (from P2 on), every model change needs a migration (`uv run alembic revision --autogenerate -m "<msg>"`, review it, `uv run alembic upgrade head`). Before that, tell the user to delete `app.db`.
- Full type annotations everywhere (mypy strict).

## 5. Test

Write tests in `tests/` (one file per resource, e.g. `tests/test_<resource>.py`) using the `client` fixture. Cover **every acceptance criterion from the ticket literally** (e.g. "2 × ₹30 + 1 × ₹50 = ₹110", "20 simultaneous orders → exactly 5 succeed") plus error paths (404, 422, 409).

## 6. Verify

Run the `quality-check` skill. Fix failures and rerun until green. Don't weaken tests or add `type: ignore` to get green without telling the user.

## 7. Commit (only when the user asks)

The brief grades Git discipline: commit in **small, meaningful steps** (e.g. `feat(offerings): add offering catalogue endpoints`, `feat(orders): compute order total on server`, `test(orders): cover inactive offering rejection`). Never use summaries like `fix`, `changes`, `wip` or `final`. Stage files by path.

## 8. Report

Summarise:
- acceptance criteria → how each is met (and the test name),
- **Assumptions** (gaps filled and what you decided),
- **Decisions & trade-offs** (what you chose and why over the alternatives),
- migrations added or `app.db` reset needed.

These feed straight into the PR template. Remind the user to note any place where they corrected the AI, since the walkthrough asks for it. Suggest `/review-ticket` next, then `/raise-pr`.
