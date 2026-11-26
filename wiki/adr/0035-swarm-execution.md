# 0035 — Swarm execution: parallel stages, integration branches and fixed role models

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-16 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-16 (spec reference GEN-020, GEN-021, MS-001): Parallel implementation in worktrees needs a place where several task branches are combined and verified before they reach `develop`; GEN-020 knows no such branch, and the spec does not say which models plan, build and review.

The owner instruction of 2026-11-26 sets the model for each role.

The spec does not answer these questions. The decision rests on: Owner instruction 2026-11-26 (CLAUDE.md). Each question is a row of the spec gap log in spec §26.

## Decision

PG-16: Owner instruction (2026-11-26): parallel stages per `2026-11-26-rootline-schedule.yaml`; task PRs merge into `integration/<stage>` branches, which pass the §7.7 integration gate and an integration review and then reach `develop` as one squash-merged PR. Models: coordinator Haiku 5.5, planner and reviewer Opus 5.5 high, implementer Sonnet 5.5 high (`CLAUDE.md`).

## Consequences

- Parallel stages run in git worktrees; task PRs merge into `integration/<stage>` branches that pass the integration gate and an integration review.
- Roles use fixed models: coordinator Haiku 5.5, planner and reviewer Opus 5.5 with high effort, implementer Sonnet 5.5 with high effort (CLAUDE.md).

## Alternatives considered

- One agent implementing tasks in sequence: not chosen because of the owner instruction of 2026-11-26 (parallel stages).
- Per-task PRs straight into `develop`: not chosen because several task branches need a place where they are combined and verified before `develop` (PG-16).

## Spec references

PG-16, GEN-020, GEN-021, MS-001, overview §7, CLAUDE.md; spec §26 rows PG-16; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
