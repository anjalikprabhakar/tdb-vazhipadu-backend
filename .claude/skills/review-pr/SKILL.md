---
name: review-pr
description: Review a GitHub pull request in this repo (correctness, API contract, tests, typing, ticket fit, PR/Git discipline) and optionally post the review with line comments. Use when the user asks to review a PR by number/URL/branch.
argument-hint: "<pr-number | url | branch> [--post]"
---

# Review PR

Arguments: $ARGUMENTS

## 1. Load the PR

- `gh pr view <pr> --json number,title,body,baseRefName,headRefName,files,commits`
- `gh pr diff <pr>`: read the **full** diff as a reviewer, not just a summary.
- `gh pr checks <pr>` (CI status, if any)
- Ticket: if the body links an issue (`Closes #n`), `gh issue view <n>`; otherwise the matching file in `doc/tickets/`.

## 2. Review

- Spawn the `code-reviewer` agent with the PR number and ticket text for an independent pass. It applies `.claude/skills/python-conventions/SKILL.md`; only that skill's blocking findings are posted.
- In parallel, check what the agent can't judge from the diff alone (the brief grades these):
  - **PR template**: Problem, Assumptions, Decisions & trade-offs and How to test are all filled in honestly. Assumptions is not empty.
  - **Scope**: one problem per PR; flag unrelated changes.
  - **Branch**: targets `main`, named `feature/p<N>-...`, based on the latest `main`.
  - **Commits**: small and meaningful; flag messages like `fix`, `changes`, `wip`, `final`.
  - **Hygiene**: no secrets, `.env` or `*.db` files committed; schema changes come with a migration (from P2 on).
  - **README**: links this PR (and earlier ones).
  - If the PR branch is checked out locally (or the user agrees to `gh pr checkout <pr>`), run the `quality-check` skill.
- Verify each agent finding by reading the code; drop false positives.

## 3. Report

```
## PR #<n>: <title>
Verdict: Approve | Request changes | Comment

### Blockers
- path:line — problem. Fix: …
### Suggestions
- path:line — …
### Ticket coverage
<criterion → met/missing>
### PR / Git discipline
<template, commits, branch, README link → ok/issue>
```

## 4. Post (only with `--post` or explicit user confirmation)

The brief requires **at least one review comment on a specific line** per PR, so always post at least one line comment. If nothing is wrong, post a genuine observation or question (e.g. a trade-off worth confirming) rather than skip it.

- Line comments: `gh api repos/{owner}/{repo}/pulls/<n>/reviews` with `event` set to `COMMENT` or `REQUEST_CHANGES` and a `comments` array of `{path, line, side: "RIGHT", body}`.
- A summary alone (`gh pr review <n> --comment --body-file <file>`) does **not** satisfy the requirement.
- Never approve a PR authored by the current user (`gh api user --jq .login`); GitHub rejects it, so use `COMMENT`.
- Next step: `/address-pr-feedback <n>`.
