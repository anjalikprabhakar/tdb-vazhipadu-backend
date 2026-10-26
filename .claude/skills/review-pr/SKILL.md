---
name: review-pr
description: >-
  Review an open GitHub pull request from this machine and post one verdict (PASS/FAIL table plus
  line comments) per .claude/conventions/review-conventions.md. Use when the user asks to review a PR
  by number, URL or branch. Invoke as "/review-pr 7". Counterpart to /fix-review-comments.
argument-hint: "[pr-number | url]"
---

# PR review (local)

PR: $ARGUMENTS

Review an open PR from your own machine and post one verdict. The method (what blocks, how to
filter, the review count, how to decide the posting mode) lives in
`.claude/conventions/review-conventions.md`; read it. This skill covers only the local I/O: how you
read the PR and how you post.

**Precondition:** `gh` installed and authenticated (`gh auth status`), and a clean working tree.
Every command is plain `gh …` or `git …`. If the main checkout has uncommitted work, do the whole
review in a separate worktree (`git worktree add <scratchpad>/pr-<PR> origin/<baseRefName>`, then run
the commands below inside it) and remove it afterwards; never stash someone's work to review.

## 1. Check out the PR

Take the PR number from the invocation or a pasted URL. With no number, use the current branch's PR:
`gh pr view --json number`. Then:

```bash
gh pr view <PR> --json number,title,body,author,headRefName,baseRefName,headRefOid,mergeable,commits
gh pr checkout <PR>
git fetch origin <baseRefName>
git diff --stat origin/<baseRefName>...HEAD
```

You now have the PR's files on disk. Read changed files from the working tree and take hunks from
`git diff origin/<baseRefName>...HEAD -- <path>`. Do not fetch file contents or diffs through the
GitHub API.

`mergeable` is the merge state (§0). If it is `CONFLICTING`, review nothing: gather only the review
count and the posting identity (step 2), then post the conflict body (step 4) and stop. If it is
`UNKNOWN`, read it once more with the same `gh pr view <PR> --json mergeable` and, if it is still
`UNKNOWN`, carry on with the review.

## 2. Gather the context the review needs

- The ticket: the issue linked in the body (`Closes #N`) with its comments,
  `gh issue view <N> --json title,body,labels,milestone,comments`, or else the matching file in
  `doc/tickets/`.
- The PR's existing discussion, so settled points are not re-raised. Read `{owner}`/`{repo}` once
  with `gh repo view --json owner,name` and substitute the literal values (`gh api graphql` does not
  fill them):

```bash
gh api graphql -f owner='<owner>' -f name='<repo>' -F pr=<PR> -f query='
query($owner: String!, $name: String!, $pr: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $pr) {
      comments(first: 100) { nodes { author { login } body } }
      reviews(first: 100) { nodes { author { login } state body } }
      reviewThreads(first: 100) { nodes { isResolved isOutdated comments(first: 50) { nodes { author { login } path line body } } } }
    }
  }
}'
```

- The review count (§4): count the review bodies and comments above that start with `# Verdict:` and
  add one.
- Who is posting: `gh api user --jq .login`, compared with `author.login` from step 1.

## 3. Review

Load the **Conventions Skills** and dispatch the **Reviewer Agents** (both in `CLAUDE.md` under
`## Project-specific`) on the changed files with the diff range and the ticket summary. In parallel,
run the `quality-check` skill on the checked-out PR and check the brief-discipline items yourself
(PR template, commits, hygiene, migration, README link). Keep only blocking findings (§2). Then
filter (§3): drop what you cannot substantiate, drop points already in discussion, and
cross-reference the open backlog:

```bash
gh issue list --state open --limit 100 --json number,title,labels,updatedAt
gh pr list --state open --limit 50 --json number,title,headRefName
```

Read the body and comments of any candidate (`gh issue view <M> --json title,body,comments`) before
deciding it already covers a finding.

## 4. Post the verdict

Write the body in the exact shape of `.claude/conventions/review-template.md`, choose the event up
front (§5), and build the line comments (§6) as `{path, line, side: "RIGHT", body}`, one per finding
on a diff line, or the single `Non-blocking:` comment on a PASS. Put them together in one JSON
payload in a temp file outside the repo,
`{"body": "<template body>", "event": "<COMMENT|REQUEST_CHANGES|APPROVE>", "commit_id": "<headRefOid>", "comments": [...]}`,
and post once:

```bash
gh api repos/<owner>/<repo>/pulls/<PR>/reviews --input <payload-file>
```

`gh pr review` alone cannot attach line comments, so it does not satisfy §6. Delete the temp file,
then return to the branch you started from (`git switch -`), or remove the worktree if you made one.

## Output

One line to the user: the verdict, the review count and the review URL. Nothing else. Next step on a
FAIL: `/fix-review-comments <PR>`.

## Project-specific

Every value this file names (**Conventions Skills**, **Reviewer Agents**, **Gate Commands**) is
registered once in `CLAUDE.md` under `## Project-specific`. Read it there. Nothing is restated here,
so nothing here can fall out of step with it.
