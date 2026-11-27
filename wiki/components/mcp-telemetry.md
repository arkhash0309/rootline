# mcp-telemetry

Status: not implemented yet — planned in W3-T06.

## Purpose

MCP server exposing metrics, logs and traces of namespace `shop` to the agent, in live or replay mode (spec §8.2).

## Requirement IDs

MCP-001 to MCP-009, MCP-020 to MCP-023, MCP-050 to MCP-053, MCP-060 to MCP-063, SEC-050 to SEC-053. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Endpoint `/mcp` (streamable HTTP, MCP revision 2026-07-28, ADR 0012) on port 8080; tools in spec §8.2.1; error envelope MCP-005. `/healthz` (liveness, 200 if the process is up), `/readyz` (200 only when the database and every hard dependency are reachable, otherwise 503 with body `{"failing":[...]}`) and `/metrics` (Prometheus exposition; the NetworkPolicy allows only namespace `observability` ingress) (ARC-020).

## Configuration

1 replica; memory request 256 Mi, limit 512 Mi (ARC-030).

## Dependencies

Prometheus, Loki, Tempo (live mode) or a snapshot bundle (replay mode, spec §8.5), Keycloak (token validation, audience check SEC-050).

## Data owned

None (ARC-001).

## Failure modes and handling

Backend unreachable: the tool returns the MCP-005 error envelope. Token with the wrong audience: rejected (SEC-050). Queries outside namespace `shop`: filtered (ARC-011).

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
