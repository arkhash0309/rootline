# 0013 — Agent tracing: Langfuse Cloud Hobby with unit budgeting

Status: accepted
Date: 2026-11-26

## Context

Agent traces, datasets and experiments need a tracing product, and non-goal NG6 excludes self-hosting Langfuse. Langfuse Cloud Hobby is free and keeps data for 30 days (OBS-023). When a free-tier limit is reached, the response is to reduce usage, never to upgrade the plan (CST-013).

This decision is row 0013 of the ADR index in spec §3. Primary reason recorded there: Free; datasets and experiments.

## Decision

Agent tracing: Langfuse Cloud Hobby with explicit unit budgeting (§20.3).

Spec §3 row 0013 is the source of this wording. It is implemented by requirement IDs OBS-020 to OBS-023.

## Consequences

- Trace units are budgeted explicitly and sampled (OBS-021).
- Langfuse is not the system of record: eval results live in `eval/runs/` and `eval.results`, investigation data in `core.*` (OBS-023).

## Alternatives considered

- LangSmith: not chosen because spec §3 requires a free product with datasets and experiments.
- Self-hosted Langfuse: not chosen, because non-goal NG6 excludes it.

## Spec references

OBS-020 to OBS-023; spec §3 row 0013.
