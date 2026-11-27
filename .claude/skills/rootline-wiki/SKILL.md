---
name: rootline-wiki
description: Use for any Rootline implementation, planning, debugging or review task in this repository - loads current project state from wiki/ before work and records what changed after work.
---

# Rootline wiki

The wiki in `wiki/` is the working memory for agents building Rootline. The spec
(`docs/superpowers/specs/2026-11-25-rootline-design.md`) says what must be true; the wiki says what is
true now and why.

## Before work

1. Read `wiki/index.md` and `wiki/status.md`.
2. Read the `wiki/components/*.md` pages for every component you will touch.
3. Read the spec sections for the requirement IDs in your task (search the spec for each ID).
4. Read the plan task you are executing in `docs/superpowers/plans/`.

## During work

- If the spec does not answer a question you need answered, follow spec §0.3: choose the simplest,
  cheapest, safest option, write an ADR in `wiki/adr/` (next free number, label `spec-gap`), and add a
  row to spec §26 in the same pull request. If the choice changes cost, security, scope or something the
  owner approved, stop and ask the owner first.
- Write facts into the wiki only after you verified them in this repository or cluster.

## After work

Perform all WIK-020 obligations in the same pull request:
1. Update the affected component or runbook pages (sections per the component template below).
2. Append an entry to `wiki/log.md`.
3. Update `wiki/status.md` if a plan task changed state.
4. Add an ADR for any new decision or deviation from the spec.
Then run `task wiki:lint` and fix every reported problem.

## Rules

- The wiki records facts verified in this repository. Mark anything not verified as
  "unverified (YYYY-MM-DD)".
- Never copy secrets, tokens, keys or passwords into the wiki.
- Keep pages factual and dated. Every component page ends with "Last verified: <date>, <commit sha7>".
- Prefer editing an existing page to creating a new one. A new page must be added to `wiki/index.md`.
- Follow the documentation rule in `CLAUDE.md`.

## Templates

### Component page (WIK-010)
    # <component>
    ## Purpose
    ## Requirement IDs
    ## Interfaces
    ## Configuration
    | Env var | Default | Meaning |
    ## Dependencies
    ## Data owned
    ## Failure modes and handling
    ## Runbook links
    ## Last verified
    <YYYY-MM-DD>, <commit sha7>

### ADR (WIK-011)
    # NNNN — <title>
    Status: proposed | accepted | superseded by NNNN
    Date: YYYY-MM-DD
    ## Context
    ## Decision
    ## Consequences
    ## Alternatives considered
    ## Spec references

### status.md (WIK-012)
    # Status
    Last updated: YYYY-MM-DD (commit <sha7>)
    ## Current milestone: Week N — <name>
    ## Done
    - <item> (PR #n, REQ IDs)
    ## In progress
    - <item> — <owner: agent|owner> — <next step>
    ## Next
    - <item>
    ## Blockers
    - <blocker> (or "None")

### log.md entry (WIK-013)
    ## YYYY-MM-DD
    - [agent|owner] <what happened> (PR #n / commit sha7)
