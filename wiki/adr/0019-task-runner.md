# 0019 — Task runner: go-task with Python helper scripts

Status: accepted
Date: 2026-11-26

## Context

The same commands must work in WSL and in CI. Shell scripts differ between environments and are hard to test, so the project restricts itself to `go-task` tasks that call typed Python scripts run by `uv`.

This decision is row 0019 of the ADR index in spec §3. Primary reason recorded there: Identical commands in WSL and CI; typed Python helpers instead of shell scripts.

## Decision

Task runner: `go-task` (`Taskfile.yml`) with Python helper scripts run by `uv`. No Makefiles, no bash scripts outside container images and CI.

Spec §3 row 0019 is the source of this wording. It is implemented by requirement IDs GEN-041, GEN-060.

## Consequences

- Anything non-trivial is a Python helper under `scripts/`.
- No Makefiles and no bash scripts exist outside container images and CI (GEN-041).

## Alternatives considered

- Make: not chosen because spec §3 requires identical commands in WSL and CI with typed Python helpers instead of shell scripts.
- npm scripts: not chosen for the same reason.

## Spec references

GEN-041, GEN-060; spec §3 row 0019.
