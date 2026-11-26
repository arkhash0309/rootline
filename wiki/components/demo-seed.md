# demo-seed

Status: not implemented yet — planned in W7-T05.

## Purpose

Kubernetes Job (ArgoCD PostSync hook, `gke` only) that loads the showcase seed dump into an empty database (spec §16.7).

## Requirement IDs

INF-050, INF-051. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

No network interface. Downloads `gs://<artifacts>/seed/v1/seed.sql.zst`, applies it, verifies the audit chain.

## Configuration

Wave 2 in the GitOps layout (INF-020); runs only when `core.incidents` is empty (INF-051).

## Dependencies

Postgres (role `rootline_migrator`), Google Cloud Storage bucket of the persistent root.

## Data owned

Loads rows into `lab`, `eval`, `core` and `audit` (INF-050).

## Failure modes and handling

Dump missing or corrupt: the Job fails and the cluster starts with an empty database. Audit chain verification fails: the Job fails.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
