# P0 – Project setup and repository bootstrap

**Labels:** `chore`, `setup`
**Branch:** initial commit on `main` (the only direct commit to `main` allowed)
**Timebox:** 5 min

## Context

The assessment must be delivered from a **public** GitHub repo named `tdb-vazhipadu-backend`, with a README and the base project on `main` before any problem branch is cut.

## Tasks

- [ ] Create public GitHub repo `tdb-vazhipadu-backend` under the personal account and add it as `origin`.
- [ ] Rename the local default branch to `main` (currently `master`).
- [ ] Commit the base FastAPI project (`src/assessment`, `tests/`, `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`, `.python-version`) and push to `main`.
- [ ] Ensure `.env`, `app.db`, `.venv/`, `.idea/` are git-ignored: **no secrets committed**.
- [ ] Replace `.github/pull_request_template.md` with the assessment's required template: `## Problem`, `## Assumptions`, `## Decisions & trade-offs`, `## How to test`.
- [ ] README: project purpose, how to run the app (`uv sync`, `uv run assessment`), how to run tests/lint/type-check, and a "Pull requests" section with placeholders for the P1–P4 links.

## Acceptance criteria

- [ ] Repo is public and `main` contains README + runnable base project.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run mypy src tests` pass on `main`.
- [ ] PR template matches the assessment template.
