---
name: fix-review-comments
description: >-
  Acts on the latest /review-pr review of an open pull request. Reads its findings (Blockers,
  Suggestions and line comments), verifies each against python-conventions, agrees the fix with you,
  commits on the PR's own branch, posts one plain-English reply table, then pushes. Use when the user
  says "fix the review comments on PR X", "address the review", or similar, with a PR number, URL, or
  the PR already in context. Invoke as "/fix-review-comments 6". Counterpart to /review-pr.
argument-hint: "[pr-number]"
---

# Fix review comments

PR: $ARGUMENTS

Turn the findings of a PR review into verified, agreed, committed fixes, then close the loop with one
reply. A finding is a claim, not an order: verify it before changing code, refute it with evidence
when it is wrong, and track it separately when it is out of the ticket's scope.

**Precondition:** `gh` installed and authenticated (`gh auth status`). The repo hooks still apply
(`.claude/hooks/format_python.py` formats and lints every edited `.py` file); fix what they flag,
never `--no-verify`.

## 1. Gather context

Take the PR number from the invocation, a pasted URL, or the PR in context. With no number, use the
current branch's PR (`gh pr view --json number`).

```bash
gh pr view <PR> --json number,title,body,author,headRefName,baseRefName,files,reviews,comments
gh api repos/{owner}/{repo}/pulls/<PR>/comments --paginate --jq '.[] | {id, path, line, original_line, author: .user.login, body}'
gh api user --jq .login
```

The **latest review whose body has a `Verdict:` line** (the `/review-pr` report format) is the review
you act on. Its findings are, in this order: each `### Blockers` bullet, each `### Suggestions`
bullet, then each of that review's line comments not already covered by a bullet. Number them 1..n;
that numbering is used everywhere below. Add any human line comments that are not yet resolved
(resolution state is in GraphQL `reviewThreads { isResolved }`; query it if unsure).

Read the ticket for intent: the issue linked in the PR body (`gh issue view <N> --json title,body,comments`)
or the matching file in `doc/tickets/`.

If the latest verdict is `Approve`, or it has no Blockers, Suggestions or line comments, and there
are no unresolved human comments, say so and stop.

## 2. Load the conventions

Load the `python-conventions` skill (the **Standard** in `CLAUDE.md` under `## Project-specific`)
when the PR touches Python. It also binds every line you write here.

## 3. Verify each finding

Decide, for every finding, before touching code, and cite what decides it:

- **Valid**: a real defect or convention violation. Cite the convention or describe the failure.
- **Invalid**: contradicts the conventions or is a false positive. Cite what makes it wrong.
- **Out of scope**: fair, but outside the PR's ticket (often it belongs to a later problem P0–P4).
  Check the open backlog first so you do not file a duplicate:

```bash
gh issue list --state open --limit 100 --json number,title
gh pr list --state open --limit 50 --json number,title,headRefName
```

  If it is already tracked, link it; otherwise it becomes an issue candidate in step 4.

## 4. Decide with the user

- **Valid** → offer the fix options with their trade-offs (`AskUserQuestion`) and apply the chosen
  one. A finding with one obvious fix needs no question; state the fix and move on.
- **Invalid** → draft a one-sentence, evidence-cited rebuttal for the reply. No code change.
- **Out of scope** → offer to file it with `gh issue create` (or link the existing issue). No code
  change here.

Settle every finding before writing code.

## 5. Apply the fixes on the PR's own branch

```bash
git status --short          # stop and ask if the tree is dirty with unrelated work
git switch <headRefName>
git pull --ff-only
```

If the branch is behind its base, merge the base in (`git merge origin/<baseRefName>`); never rebase
or force-push a branch under review. Make the edits, adding or adjusting tests where behaviour
changes, and run the `quality-check` skill (the **Gate Commands**) until green. If a fix changes an
assumption or decision, update the PR body's Assumptions / Decisions & trade-offs
(`gh pr edit <PR> --body-file <file>`).

Commit atomically, one finding per commit, with a Conventional Commit message that says what changed
(e.g. `fix(orders): reject duplicate offering ids in one order`), never `fix`, `wip` or
`address review`. Stage with `git add -p`. **Commit, but do not push yet.**

## 6. Reply first, then push

Where a CI review runs on push, it snapshots the discussion at the start of its run; a reply posted
after the push is invisible to that review and the same findings come back. So post the reply first.

Write the reply to a temp file outside the repo (never commit it): a table with one row per finding
in step 1's order. **File** is the finding's `path:line`, **Issue** is the finding restated in at
most one sentence, and **Fix** is what was done, at most 25 words: the commit that fixed it, or
`Not changed:` plus the one-line reason, or `Tracked in #N`. Nothing else goes in the body except a
first line `Reply to review <n>` (the review count you acted on); when the review author is the same
login as the viewer that line reads `Reply to my own review <n>`.

```markdown
Reply to my own review 2

| No. | File | Issue | Fix |
|---|---|---|---|
| 1 | `src/assessment/api/orders.py:42` | Duplicate offering ids in one order are summed silently. | Fixed in a1b2c3d: rejected with 422 and a test. |
| 2 | `pyproject.toml:36` | `xfail_strict` splits the asyncio options. | Not changed: grouping is cosmetic; ruff and pytest ignore order. |
```

The brief requires each line comment to be answered by a follow-up commit or a short reply, so also
reply in each line-comment thread with its row's **Fix** text:
`gh api repos/{owner}/{repo}/pulls/<PR>/comments/<comment_id>/replies -f body="..."`.

Then:

```bash
gh pr comment <PR> --body-file <reply-file>
git push            # never --force
```

Confirm the push landed (reconcile and push again if it was rejected), then delete the reply file.

## Output

The same table you posted, and the PR URL. Next step: `/merge-pr <PR>`.

## Project-specific

Every value this file names (**Standard**, **Gate Commands**) is registered once in `CLAUDE.md`
under `## Project-specific`. Read it there. Nothing is restated here, so nothing here can fall out of
step with it.
