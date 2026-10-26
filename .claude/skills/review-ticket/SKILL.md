---
name: review-ticket
description: Verify that the current branch's changes fully satisfy a ticket — acceptance-criteria gap analysis plus an independent code review — before raising a PR. Use when the user asks to review/check/validate work against a ticket.
argument-hint: "<ticket text | #issue-number> [base-branch]"
---

# Review ticket implementation

Arguments: $ARGUMENTS

## 1. Gather inputs

- Ticket: `gh issue view <n>` if an issue number was given; for a problem ID (`P1`) or path, the matching file in `doc/tickets/`; otherwise the pasted text. If no ticket is given, look for one in the conversation or ask.
- Base branch: second argument, else `main` (fall back to the default branch).
- Changes: `git diff <base>...HEAD` plus uncommitted work (`git diff`, `git status` for untracked files).

## 2. Acceptance-criteria matrix

List each acceptance criterion (derive them if the ticket doesn't number them) and, for each, find the code and the test that prove it. Read the code — don't infer from file names.

| # | Criterion | Implemented in | Tested by | Status |
|---|-----------|----------------|-----------|--------|

Status is ✅ met, ⚠️ partial, or ❌ missing. Each acceptance criterion from the brief must have a test that asserts it literally (e.g. total ₹110; exactly 5 of 20 concurrent orders succeed; 00:15 IST counts on that date). Also flag **scope creep**: changes not traceable to any criterion.

Then list the ticket's **Decisions to make** and, for each, the choice the code actually makes. Every one must appear as an Assumption or Decision in the PR. Flag any that are undecided or implicit.

Also check, as the brief requires: all errors use the one shared JSON error format; money never goes through `float`; schema changes come with a migration (from P2 on).

## 3. Independent code review

Spawn the `code-reviewer` agent with the diff range and the ticket text (it applies the `python-conventions` standard). Do not pass your own conclusions from step 2 — the point is an unanchored second read.

## 4. Quality gates

Run the `quality-check` skill and include its result.

## 5. Verdict

Report:

1. The matrix, plus the assumptions/decisions list (ready to paste into the PR).
2. Reviewer findings you confirmed (drop ones you checked and found wrong, saying why).
3. Gate results.
4. Verdict: **Ready for PR** or **Needs work** with the ordered list of fixes.

Don't fix anything unless the user asks; offer to.
