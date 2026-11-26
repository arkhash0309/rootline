# api

Status: not implemented yet — planned in W4-T06.

## Purpose

FastAPI platform API: incidents, investigations, proposals, approvals, eval import, audit log, job queue and internal endpoints for the agent and the gate (spec §12).

## Requirement IDs

API-001 to API-007, API-040, API-050, API-051, API-060 to API-062, API-070, DB-001 to DB-003, SEC-130, ARC-001, ARC-020. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Public endpoints `/v1` (spec §12.3), webhooks (spec §12.4), internal endpoints `/internal/v1` (spec §12.5), problem+json errors with the codes of API-002. `/healthz` (liveness, 200 if the process is up), `/readyz` (200 only when the database and every hard dependency are reachable, otherwise 503 with body `{"failing":[...]}`) and `/metrics` (Prometheus exposition; the NetworkPolicy allows only namespace `observability` ingress) (ARC-020).

## Configuration

Replicas 1 locally and 2 on GKE; memory request 192 Mi, limit 384 Mi (ARC-001, ARC-030). Container port 8080, ClusterIP Service port 80, DNS `api.rootline.svc.cluster.local` (ARC-020). Container security context per INF-022: `runAsNonRoot: true`, `runAsUser: 10001`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault`.

## Dependencies

Postgres (role `rootline_api`), Keycloak (token validation), `gate` (`POST /internal/v1/proposals/{id}/reevaluate`), `faultlab`.

## Data owned

Writer of schemas `core`, `audit` and `eval` (ARC-001, DB-002).

## Failure modes and handling

Postgres unreachable: `/readyz` returns 503 with `{"failing":["postgres"]}` (ARC-020). Invalid input: RFC 9457 problem+json with an API-002 code. Gate unreachable: approval is stored and re-evaluation is retried (spec §11.7).

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
