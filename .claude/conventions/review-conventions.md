# Review conventions

The method every PR review in this repo follows: what blocks, how findings are filtered, how reviews
are counted and how the verdict is posted. `/review-pr` covers only the I/O; the body shapes are in
`review-template.md`. `/fix-review-comments` reads reviews written to this method.

## §0 Merge state

Read `mergeable` before reviewing. `CONFLICTING` is an automatic FAIL: review nothing and post the
conflict body from `review-template.md`. `UNKNOWN` means GitHub is still computing it; read it once
more, and if it is still `UNKNOWN`, review as normal.

## §1 Scope

Only added or modified lines in `git diff origin/<base>...HEAD` are judged, plus the PR and branch
discipline the brief grades. Existing code the PR does not touch is never a finding.

## §2 What blocks

A finding is posted only if it is one of these:

1. **Defect**: wrong behaviour, a crash, data loss or a security hole, shown with a concrete input or
   state that triggers it.
2. **Standard**: a rule listed under "What a blocking finding is" in the **Conventions Skills**
   (`python-conventions`), on a changed line.
3. **Ticket**: an acceptance criterion of the linked issue or `doc/tickets/` file that is not met.
4. **Gates**: any of the **Gate Commands** fails on the PR head.
5. **Brief discipline**: a PR template section is empty, or Assumptions is empty or "None"; `.env`,
   `*.db` or a secret is committed; a schema change has no Alembic migration (P2 on); a commit message
   is a bare `fix`, `wip`, `changes` or `final`; a P1–P4 PR is not linked in the README; the PR mixes
   more than one problem.

Style preferences, "consider" remarks and praise are never posted as findings.

## §3 Filter

Drop a candidate finding when any of these holds:

- **Unsubstantiated**: you cannot name the `path:line` and the failure, having read the code (not
  just the hunk). Agent findings are verified the same way.
- **Already in discussion**: raised in an earlier review, in a resolved thread, or answered by a
  reply, unless the PR has since regressed it.
- **Already tracked**: an open issue or PR covers it. Read its body and comments before deciding.

## §4 Review count

Count the PR's review bodies and comments that start with `# Verdict:` and add one. That number is
`<n>` in the template's first line.

## §5 Verdict and posting mode

**PASS** when no finding survives §3, **FAIL** otherwise. Post exactly one review:

| Viewer is the PR author | Verdict | Event |
|---|---|---|
| yes | either | `COMMENT` (GitHub rejects approving your own PR) |
| no | FAIL | `REQUEST_CHANGES` |
| no | PASS | `APPROVE` |

## §6 Line comments

The brief requires at least one line comment on every PR. Each finding on a line in the diff is also
posted as a line comment on that line, with the finding's Issue and Fix text. A PASS with no findings
still posts one line comment: a genuine observation or question on a changed line (a trade-off worth
confirming), starting `Non-blocking:`.

## §7 Writing

Plain English. **Issue** is one sentence naming the failure, not the fix. **Fix** is at most 25 words
and says what to change. No hedging ("might", "perhaps"), no praise, no restating the diff.
