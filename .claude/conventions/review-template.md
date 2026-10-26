# Review template

The exact body shapes `/review-pr` posts. Rules for what goes in them are in
`review-conventions.md`. Rows are numbered from 1 in the order Defect, Standard, Ticket, Gates,
Brief discipline (§2); `/fix-review-comments` replies with the same **No.**, **File** and **Issue**.

## FAIL

```markdown
# Verdict: ❌ FAIL

Review <n> of #<PR>: <title>

| No. | File | Issue | Fix |
|---|---|---|---|
| 1 | `src/assessment/services/orders.py:42` | An order with the same offering twice is priced once. | Merge duplicate offering ids before pricing, or reject them with 422; add a test. |
| 2 | `PR body` | Assumptions says "None". | List the gaps in the ticket you filled, e.g. how phone numbers are normalised. |
```

`File` is `path:line` (or `path:start-end`) in backticks; a finding with no line, such as the PR body,
a commit message or the README link, names what it is about instead.

## PASS

```markdown
# Verdict: ✅ PASS

Review <n> of #<PR>: <title>

No blocking findings. Gates: pytest, ruff check, ruff format, mypy all green.
```

## Conflict

```markdown
# Verdict: ❌ FAIL

Review <n> of #<PR>: <title>

The branch conflicts with `<base>`, so it was not reviewed. Merge `<base>` into the branch, resolve
the conflicts, push, and request review again.
```
