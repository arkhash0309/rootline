# postgres

Status: not implemented yet — planned in W1-T11.

## Purpose

CloudNativePG cluster `rootline-pg` with Postgres 16 and pgvector for all Rootline and Keycloak data (spec §13).

## Requirement IDs

DB-001, DB-002, DB-003, ARC-001, ARC-010, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Port 5432 in namespace `rootline-data`. Databases `rootline` (owner `rootline_migrator`) and `keycloak` (owner `keycloak`). Roles and grants: DB-002.

## Configuration

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

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
