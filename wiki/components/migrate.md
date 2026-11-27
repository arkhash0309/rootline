# migrate

Status: not implemented yet — planned in W2-T02.

## Purpose

Kubernetes Job (ArgoCD PreSync hook) that runs `alembic upgrade head` with the `rootline/api` image as role `rootline_migrator` (spec §13).

## Requirement IDs

DB-001 to DB-003, DB-010, ARC-001. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

No network interface. Command `alembic upgrade head`; exit code 0 on success, non-zero on failure.

## Configuration

Runs in namespace `rootline` before the umbrella chart resources (INF-020 wave 1).

## Dependencies

Postgres cluster `rootline-pg` and the password Secret of role `rootline_migrator` (ADR 0032).

## Data owned

All schema migrations; owner of schemas `core`, `lab`, `eval`, `audit`, `bff` (DB-002).

## Failure modes and handling

Migration fails: the Job fails, the PreSync hook fails and ArgoCD does not sync the rest of the `rootline` application.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
