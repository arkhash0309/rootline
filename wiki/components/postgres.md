# postgres

Status: chart implemented in W1-T11 (`deploy/charts/postgres`); rendered and tested, not yet deployed.

## Purpose

CloudNativePG cluster `rootline-pg` with Postgres 16 and pgvector for all Rootline and Keycloak data (spec §13).

## Requirement IDs

DB-001, DB-002, DB-003, ARC-001, ARC-010, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Port 5432 in namespace `rootline-data`. Databases `rootline` (owner `rootline_migrator`) and `keycloak` (owner `keycloak`). Roles and grants: DB-002.

## Configuration

Chart `deploy/charts/postgres` (`Chart.yaml`, `values.yaml`, `values-gke.yaml`, `templates/cluster.yaml`, `templates/database-keycloak.yaml`, `templates/networkpolicies.yaml`). `values.yaml` `image` is `ghcr.io/cloudnative-pg/postgresql:16@sha256:34cd4159d07b3410a1b29da35072e2e927a0905e717a61afa3814624a2e8859a` (versions.yaml key `postgres-image`; `test_cnpg_image_pinned_by_digest` fails when they differ). Managed roles `rootline_migrator`, `rootline_api`, `rootline_agent`, `rootline_faultlab`, `rootline_console`, `keycloak` (`ensure: present`, `login: true`) read passwords from Secrets `pg-<role with - for _>` in `rootline-data` (created by ESO generators, PG-10; this chart creates no Secret). Bootstrap `initdb`: database `rootline`, owner `rootline_migrator`, secret `pg-rootline-migrator`. CNPG `Database` `keycloak` (owner `keycloak`, sync wave `1`, reclaim policy `retain`). NetworkPolicies in `rootline-data`: 5432 from `rootline` and `keycloak`; 8000 and 5432 from `cnpg-system`; same-namespace traffic; egress TCP 443 and 6443 to any address (kube-apiserver). The `CREATE EXTENSION vector` check (DB-001) is not yet run: it needs the cluster (W1-T12 Step 5).

1 instance, 5 Gi storage (`local-path` locally, `standard-rwo` on GKE), image `ghcr.io/cloudnative-pg/postgresql:16`, `shared_buffers=128MB`, `max_connections=100`, `log_min_duration_statement=500` (DB-001). Memory: instance 384 Mi request, 768 Mi limit; CNPG operator 96 Mi request, 256 Mi limit (ARC-030).

## Dependencies

CloudNativePG operator (sync wave -3), External Secrets generators for role passwords (ADR 0032).

## Data owned

Everything in `rootline` and `keycloak` databases. Backups are disabled in all environments (ADR 0007, DB-001).

## Failure modes and handling

Instance down: every service `/readyz` returns 503 with `postgres` in `failing` (ARC-020). `CREATE EXTENSION vector` fails: build a derived image and record it in `versions.yaml` (DB-001). Data loss: restore from snapshots and the seed dump (spec §16.7).

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed. Verified by `helm template` of `deploy/charts/postgres` (`tests/repo/test_observability_values.py`); not deployed to a cluster yet, pgvector unverified (2026-11-27).
