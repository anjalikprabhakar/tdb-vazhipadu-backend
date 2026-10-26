---
name: merge-pr
description: Merge a reviewed PR into main once its review comments are addressed, then pull main so the next problem starts from it. Use only when the user explicitly asks to merge a PR.
argument-hint: "<pr-number> [--merge]"
disable-model-invocation: true
---

# Merge PR

Arguments: $ARGUMENTS

## 1. Preconditions (stop and report if any fail)

- `gh pr view <n> --json state,baseRefName,body,mergeable,headRefName`: open, base `main`, mergeable.
- The PR body has all four template sections, and **Assumptions** is non-empty.
- `gh api repos/{owner}/{repo}/pulls/<n>/comments` shows **at least one line comment**, and each has a reply or a follow-up commit after it.
- `gh pr checks <n>` is green (if CI exists). Otherwise run the `quality-check` skill on the PR branch.
- The README on the PR branch links this PR.

## 2. Merge

- Squash by default (`gh pr merge <n> --squash --delete-branch`), or a merge commit with `--merge`. Both are fine per the brief. Never use `--admin` to bypass checks.

## 3. Sync

- `git checkout main && git pull`. The next problem's branch must start from this.
- `git log --oneline -3` to confirm the merge landed.

## 4. Report

Merged PR URL, the new `main` head, and the next ticket in order (P1 → P2 → P3 → P4).
