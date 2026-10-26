---
name: quality-check
description: Run all quality gates for this repo (pytest, ruff lint, ruff format check, mypy strict) and report pass/fail with the failing output. Use before committing, before a PR, or whenever asked to "run checks/tests/lint".
argument-hint: "[--fix]"
---

# Quality check

Run each gate from the repo root and capture its result. Run all four even if an early one fails.

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
```

Also run these when they apply (the brief requires "all tests pass" and "no secrets committed"):

```bash
# migrations (only if alembic.ini exists): schema builds from an empty DB
APP_DATABASE_URL=sqlite+aiosqlite:///./.migration-check.db uv run alembic upgrade head; rm -f .migration-check.db
# secrets: nothing like .env or *.db is tracked
git ls-files | grep -E '(^|/)\.env$|\.db$' || echo "no secrets/db tracked"
```

Check the actual settings field name in `config.py` before overriding the DB URL.

With `--fix` ($ARGUMENTS), first run `uv run ruff check --fix .` and `uv run ruff format .`, then the gates above. Fix test and mypy failures in code only if the user asked for fixes.

Report as:

| Gate | Result |
|------|--------|
| pytest | ✅ N passed / ❌ N failed |
| ruff check | ✅ / ❌ N issues |
| ruff format | ✅ / ❌ N files |
| mypy | ✅ / ❌ N errors |
| migrations | ✅ / ❌ / n/a |
| secrets | ✅ / ❌ files |

Below the table, quote only the relevant failure output (test names + assertion, file:line for lint/type errors). Never report a gate as passing that you didn't run.
