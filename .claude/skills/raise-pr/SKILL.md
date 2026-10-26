---
name: raise-pr
description: Commit the current work, push the branch and open a GitHub pull request filled in from .github/pull_request_template.md. Use only when the user explicitly asks to raise/open/create a PR.
argument-hint: "[ticket ref] [--draft] [--base <branch>]"
disable-model-invocation: true
---

# Raise PR

Arguments: $ARGUMENTS

## 1. Preconditions

- `git remote -v` must show a remote (the public repo `tdb-vazhipadu-backend`). If none, stop and tell the user to add one (`git remote add origin <url>`); don't create repos on their behalf.
- **Never commit to `main`.** If on `main`/`master`, stop and create a branch first: `feature/p<N>-<slug>`.
- The branch must be based on the latest `main` (`git fetch origin && git merge-base --is-ancestor origin/main HEAD`). If not, tell the user and offer to rebase before pushing.
- Run the `quality-check` skill. If anything fails, stop and report. Don't open a PR on a red build unless the user says to (then open it as `--draft` and say why in the body).

## 2. Commit

- `git status` and `git diff`: review what will be committed. Never commit `.env`, `*.db`, or caches (they're gitignored; double-check nothing slipped in). **No secrets.**
- Stage files explicitly by path (not `git add -A`).
- Prefer **several small, meaningful commits** over one big one (e.g. model + migration, endpoints, tests). Conventional Commits: `<type>(<scope>): <summary>` (types: feat, fix, refactor, test, docs, chore). The summary says what changed, e.g. `feat(orders): compute order total on server`. **Never** use bare summaries like `fix`, `changes`, `wip` or `final`. Add a `Refs: <ticket>` line when there is a ticket.

## 3. Push

`git push -u origin <branch>`. Never force-push.

## 4. Open the PR

- Read `.github/pull_request_template.md` and fill **every** section from the actual diff (`git diff <base>...HEAD`) and the ticket:
  - **Problem**: what this PR solves (1–2 lines), plus `Closes #<n>` if the ticket is a GitHub issue.
  - **Assumptions**: every gap in the problem statement you filled and what you decided. This section is mandatory and must never be empty or "None".
  - **Decisions & trade-offs**: what you chose and why over the alternatives.
  - **How to test**: commands (`uv run pytest ...`, migrations), sample `curl` requests, test file names.
- Delete HTML comments.
- Title: a descriptive summary prefixed with the problem, e.g. `P1: Offerings and orders API`.
- Write the body to a temp file in the scratchpad and run:
  `gh pr create --base main --title "<title>" --body-file <file> [--draft]`
- End the body with the PR attribution line from the session's instructions.

## 5. Link the PR in the README

The README must link all 4 PRs, and `main` can't be committed to directly, so do it on this branch:
- Add the new PR URL under the README's "Pull requests" section (e.g. `- P1 – Offerings and Orders API: <url>`).
- Commit `docs(readme): link P<N> pull request` and push.

## 6. Report

Give the PR URL and anything the reviewer should know (assumptions, migrations, `app.db` reset needed). Next step: `/review-pr <n>`. The brief requires at least one line-level review comment to be left and addressed before merging.
