---
name: address-pr-feedback
description: Fetch unresolved review comments on a PR, fix the valid ones, and reply. Use when the user asks to address, resolve, or fix PR review comments/feedback.
argument-hint: "<pr-number>"
---

# Address PR feedback

PR: $ARGUMENTS (if empty, use `gh pr view --json number` for the current branch)

The brief requires every PR to have at least one line review comment that is **addressed with a follow-up commit or a short reply explaining why no change is needed** before merge.

## 1. Collect feedback

- `gh pr view <n> --json headRefName,reviews,comments`
- Line comments: `gh api repos/{owner}/{repo}/pulls/<n>/comments`
- If there are **no line comments**, stop and tell the user to run `/review-pr <n>` first.
- Make sure the PR branch is checked out (`git branch --show-current` vs `headRefName`); if not, ask before switching.

## 2. Triage

Check each comment against the `python-conventions` skill: a comment that names a **Blocking in review** rule or a real defect is a fix; a style preference may be answered with a reply. For each comment, decide: **fix**, **discuss** (disagree, with a concrete reason), or **already done**. Show the triage table to the user before editing if any item is "discuss" or the change is large.

## 3. Fix

Make the changes, adding/adjusting tests where behaviour changes. Run the `quality-check` skill until green. If a fix changes an assumption or decision, update the PR body's Assumptions / Decisions & trade-offs (`gh pr edit <n> --body-file <file>`).

## 4. Commit and reply (ask before pushing)

- Commit per logical fix with a message that says what changed, e.g. `fix(orders): reject duplicate offering ids in one order`. Never use a vague summary like `fix` or `address review feedback`. Push with `git push` (never force).
- Reply to **every** line comment: `gh api repos/{owner}/{repo}/pulls/<n>/comments/<comment_id>/replies -f body="..."`. Name the commit that fixed it, or explain briefly why no change is needed.

## 5. Report

List each comment → outcome (commit sha or reply), plus anything left for the reviewer to decide. Next step: `/merge-pr <n>`.
