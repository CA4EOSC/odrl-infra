---
name: skill-github
description: Post a progress update on a GitHub issue that tracks ODRL / CDIF work. Use when the user asks to "update the issue", "comment on issue #N", "log progress on GitHub", "track this in the issue", close or relabel a tracking issue, or after finishing work that implements an issue in CDIF4EOSC/.github-private. It reads the issue, collects what changed in odrl-infra (diff, commits, branch, test and UI checks), and posts a structured comment with gh.
---

# Updating tracking issues on GitHub

The work in this repo (`CDIF4EOSC/odrl-infra`) is tracked as issues in
**`CDIF4EOSC/.github-private`**, not in this repo. Unless the user names another repo, every
`gh issue` command uses `-R CDIF4EOSC/.github-private`.

A comment on an issue is visible to the whole team, so it must say only what is true and
checked. Never post a comment claiming something works if you did not run or see it.

## 1. Find the issue

- The user gives a number, a URL (`.../issues/24#event-...`, the `#event` part can be ignored),
  or describes the work. For a description, find it with:
  `gh issue list -R CDIF4EOSC/.github-private --search "<words>" --state all`
- If two or more issues fit, ask which one before posting.

## 2. Read it first

```bash
gh issue view <N> -R CDIF4EOSC/.github-private --json title,body,state,labels,comments \
  > "$SCRATCH/issue.json"
```

Read the body and all comments (use Python or jq to print them; the plain `--comments`
view can hide the body). Note:
- what the issue asks for, and any example JSON-LD or spec in the comments,
- what earlier updates already said, so the new comment adds to them and does not repeat them.

## 3. Collect what was actually done

From odrl-infra:

```bash
git branch --show-current
git status --short
git log --oneline origin/main..HEAD     # commits for this work
git diff --stat                          # uncommitted changes
```

Plus what was checked in this session: tests run (command and result), UI checked in the
browser, JSON-LD output seen, validation results. Keep failures and pre-existing problems:
those belong in the update too.

If the work is committed and pushed, link commits as
`CDIF4EOSC/odrl-infra@<sha>` and PRs as `CDIF4EOSC/odrl-infra#<n>` so GitHub cross-links them.
If it is not committed, say so ("not yet committed, branch `<name>`").

## 4. Write the comment

Write it to a file in the scratchpad, then post with `--body-file` (never inline `--body`
for multi-line text). Use this shape and drop sections that have nothing in them:

~~~markdown
**Status:** <Done | In progress | Blocked> (branch `<branch>`, <committed @sha / not yet committed>)

**What changed**
- UI: <what the user now sees or does differently>
- JSON-LD: <how the policy output changed>
- Backend / vocabularies: <endpoints, config/*.ttl, validation>

**Example output**
```json
<smallest JSON-LD snippet showing the change>
```

**Checked**
- <tests: command and result, e.g. tests/test_cdif_vocab.py: 9 passed>
- <UI: what was clicked and what was seen>

**Known issues**
- <failures, including ones that already existed before this change>

**Open questions**
- <decisions the team needs to make, each one a clear question>
~~~

Writing rules:
- Plain, short sentences. The readers are the CDIF SubGroups, not only developers.
- Use the vocabulary names the team uses: CV1 actions, CV2 purposes, CV3 other constraints,
  CV4 duty actions, and the ODRL terms (`odrl:duty`, `odrl:refinement`, ...).
- Put code, terms and handles in backticks. Do not write a bare `@name` unless the user asked to
  notify that person.
- No secrets, tokens, private keys, or personal emails.

## 5. Post it

Show the user the comment text (or a short summary of it) and the target issue, then post:

```bash
gh issue comment <N> -R CDIF4EOSC/.github-private --body-file "$SCRATCH/comment.md"
```

Give the user the comment URL that `gh` prints.

To fix a comment you just posted, edit it instead of posting a second one:
`gh issue comment <N> -R CDIF4EOSC/.github-private --edit-last --body-file "$SCRATCH/comment.md"`

## 6. State changes: only when asked

Do these only when the user asks for them in this conversation:

- Close: `gh issue close <N> -R CDIF4EOSC/.github-private --comment "<why>"`
  (`--reason "not planned"` if dropped)
- Reopen: `gh issue reopen <N> -R CDIF4EOSC/.github-private`
- Labels: `gh issue edit <N> -R CDIF4EOSC/.github-private --add-label <l> --remove-label <l>`
  (check names with `gh label list -R CDIF4EOSC/.github-private`)
- New issue for follow-up work found along the way: propose title and body first, create it
  with `gh issue create -R CDIF4EOSC/.github-private --title ... --body-file ...` only after the
  user agrees, and mention the new number in the update.

## Checklist before posting

- [ ] Right repo (`CDIF4EOSC/.github-private`) and right issue number
- [ ] Every claim in "Checked" was really run or seen in this session
- [ ] Pre-existing failures are reported as such, not hidden
- [ ] Commit state is correct (committed / pushed / not yet committed)
- [ ] No bare `@mentions`, no secrets
