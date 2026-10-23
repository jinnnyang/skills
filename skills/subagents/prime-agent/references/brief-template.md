# Delegation Task Brief — template

prime-agent sees none of this conversation. A chat summary is not a spec.
Write the brief to a file and point the child at it; the file outlives the
run (ISSUE-002: a timeout kill discards the report, never the files) and
gives a re-dispatch a durable spec to resume from.

Fill every section; delete nothing. If a section feels unnecessary, that
usually means the task is too small to delegate.

```markdown
# Task: <one-line imperative>

## Context
- Repo: <absolute path> (git branch <branch>, expected clean unless noted)
- Study first: <paths to sibling/reference work that defines the pattern to follow>
- Reference directory (READ-ONLY, DO NOT COPY TEXT OR CODE FROM IT):
  <absolute path> — you may read it to understand the domain; every line
  you produce must be your own. (Only for original-work tasks.)

## What to build
<concrete deliverables, as a numbered list of files and behaviors>

## Hard requirements
- [ ] <constraint, e.g. "no text copied from the reference">
- [ ] <test requirement, e.g. "every script passes end-to-end: command chain">
- [ ] <environment fact, e.g. "deps available: X, Y — do NOT assume Z is installed">

## When done
- cd <repo root> && <exact verification commands to run>
- git add -A && git commit -m "<exact commit message>"   # or: do NOT commit
- Do not touch anything outside <scope>.

## Report back
List exactly:
1. Files created (paths)
2. Commands run and their outcomes (paste the final verify output)
3. Anything you could not verify and why
```

## Why these sections earn their place

- **Report back** exists because the final summary is a self-report and
  self-reports drift. Demanding pasted verify output makes drift visible:
  in one real run the child reported "validate passes" while the final
  artifact failed validation — its test chain covered an intermediate
  state, not the delivered one. Which is why the parent re-runs the
  verify commands itself afterward (SKILL.md, Verification protocol).
- **READ-ONLY reference marking** is what makes original-work delegation
  safe: the child is told it may study but not copy, which channels the
  inevitable influence into ideas rather than text.
- **Exact commit message + scope fence** keep an autonomous 140-turn run
  from committing outside its lane.

## Sizing

A brief is the unit of delegation, not a slice of a conversation. If the
task needs steering mid-flight, prime-agent one-shot mode cannot be
steered — split into: task 1 (exploration/plan, read-only), review, task
2 (implementation). A task that cannot finish inside the timeout should
be split at the brief stage, not rescued at the timeout stage.
