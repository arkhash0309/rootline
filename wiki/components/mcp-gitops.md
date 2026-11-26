# mcp-gitops

Status: not implemented yet — planned in W3-T08.

## Purpose

MCP server giving the agent read access to repository `rootline-env` and, from week 5, the `propose_fix` tool (spec §8.4).

## Requirement IDs

MCP-001 to MCP-009, MCP-040, MCP-041, MCP-050 to MCP-053, SEC-050 to SEC-053, SEC-080. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Endpoint `/mcp` on port 8080; tools in spec §8.4. `/healthz` (liveness, 200 if the process is up), `/readyz` (200 only when the database and every hard dependency are reachable, otherwise 503 with body `{"failing":[...]}`) and `/metrics` (Prometheus exposition; the NetworkPolicy allows only namespace `observability` ingress) (ARC-020).

## Configuration

1 replica; memory request 128 Mi, limit 256 Mi (ARC-030).

## Dependencies

GitHub (App `rootline-agent`, installed only on `rootline-env`), ArgoCD, Keycloak, `api`.

## Data owned

None (ARC-001).

## Failure modes and handling

GitHub error: the MCP-005 error envelope. Proposal outside the catalogue: rejected by schema validation (POL-020).

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
