# agent

Status: not implemented yet — planned in W4-T10.

## Purpose

LangGraph planner/executor workers that investigate incidents through the three MCP servers and call Claude models through `rootline_llm` (spec §9).

## Requirement IDs

AGT-001 to AGT-006, AGT-010, AGT-020 to AGT-026, AGT-030 to AGT-035, AGT-040, AGT-050 to AGT-055, AGT-060 to AGT-066, AGT-070 to AGT-073, AGT-080 to AGT-083, AGT-090 to AGT-093, AGT-100. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

No public API. Port 8080 serves `/healthz`, `/readyz` and `/metrics` only (ARC-001). Workers claim jobs from `core.jobs` (AGT-030) and stream steps to `api` (AGT-034).

## Configuration

2 replicas locally and on GKE; memory request 256 Mi, limit 512 Mi per replica (ARC-001, ARC-030). Reduction rule ARC-031 step 4 lowers it to 1 replica.

## Dependencies

`api`, `mcp-telemetry`, `mcp-k8s`, `mcp-gitops` (OAuth 2.0 resource servers), Keycloak, Postgres (role `rootline_agent`), Anthropic API, Langfuse Cloud.

## Data owned

Schema `langgraph` (LangGraph tables); updates only the `core.jobs` columns listed in DB-002.

## Failure modes and handling

Anthropic API error: retry and repair rules of AGT-062. Budget exhausted: the investigation ends as `inconclusive` (spec §9.10). Worker crash: the lease expires and the reaper requeues the job (AGT-030).

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
