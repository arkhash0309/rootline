# 0024 — Evaluation execution: host-side runner with Message Batches

Status: accepted
Date: 2026-11-26

## Context

Sweeps replay at least 300 scenarios and must stay inside the USD 48 evaluation cap (CST-001). Running the runner on the host removes the need for cluster memory, and the Message Batches API halves the price when requests are submitted in lockstep.

This decision is row 0024 of the ADR index in spec §3. Primary reason recorded there: 50% cost reduction; no cluster RAM needed.

## Decision

Evaluation execution: Eval runner runs on the host, outside the cluster, with replay-mode MCP servers in-process. Sweeps use the Anthropic Message Batches API in lockstep mode (§15.8).

Spec §3 row 0024 is the source of this wording. It is implemented by requirement IDs EVL-062, C13.

## Consequences

- Ollama runs in WSL while the cluster is stopped.
- Replay-mode MCP servers run in-process in the runner (spec §8.5, §15.8).

## Alternatives considered

- In-cluster eval jobs: not chosen because spec §3 requires no cluster RAM for evaluation.

## Spec references

EVL-062, C13; spec §3 row 0024.
