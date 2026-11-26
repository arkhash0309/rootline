# gate

Status: not implemented yet — planned in W5-T05.

## Purpose

Policy gate: evaluates proposals with an OPA sidecar, manages approvals, merges pull requests, triggers ArgoCD sync and verifies recovery (spec §11).

## Requirement IDs

POL-001, POL-010, POL-020 to POL-032, POL-040, POL-041, POL-050 to POL-052, POL-060, POL-070, POL-080, SEC-081, SEC-132. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Gate on port 8080 and OPA on port 8181 (localhost only) (ARC-001); OPA input and decision: spec §11.5; gate loop: spec §11.6. `/healthz` (liveness, 200 if the process is up), `/readyz` (200 only when the database and every hard dependency are reachable, otherwise 503 with body `{"failing":[...]}`) and `/metrics` (Prometheus exposition; the NetworkPolicy allows only namespace `observability` ingress) (ARC-020).

## Configuration

1 replica; memory request 128 Mi plus 64 Mi OPA, limit 256 Mi plus 128 Mi OPA (ARC-030).

## Dependencies

OPA sidecar, `api` internal endpoints (the gate has no database role, DB-002), GitHub App `rootline-gate`, ArgoCD API.

## Data owned

Proposal state transitions, written through `api` (ARC-001).

## Failure modes and handling

OPA unreachable: the proposal is not merged and stays in its current state (default-deny, ADR 0008). GitHub or ArgoCD error: the behaviour is specified by the gate loop in spec §11.6.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
