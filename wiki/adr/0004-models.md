# 0004 — Models: Haiku 5.5 small, Sonnet 5.5 large, Ollama local baseline

Status: accepted
Date: 2026-11-26

## Context

The benchmark story is cost versus accuracy within a total budget of USD 100, of which the LLM lines sum to USD 75 (CST-001). Two Claude models cover the trade-off: `claude-haiku-5-5` for cheap, high-volume nodes and `claude-sonnet-5-5` for the nodes that need stronger reasoning. A local Ollama model gives a no-cost comparison point, chosen by a pilot (spec §9.5.4).

This decision is row 0004 of the ADR index in spec §3. Primary reason recorded there: Cost-vs-accuracy story within budget.

## Decision

Models: Small: `claude-haiku-5-5`. Large: `claude-sonnet-5-5`. Local baseline: Ollama model chosen by pilot (§9.5.4).

Spec §3 row 0004 is the source of this wording. It is implemented by requirement IDs AGT-050, AGT-051, C3.

## Consequences

- The `routed` configuration is the default (spec §9.5).
- The owner may add `claude-opus-5-5` to the configuration catalogue through a new ADR; the models used to build Rootline (CLAUDE.md) are a separate choice.

## Alternatives considered

- `claude-opus-5-5` as a large model (listed in the plan at USD 4 input and USD 20 output per million tokens): not chosen because `claude-sonnet-5-5` as the large model already gives the cost-versus-accuracy story within the USD 75 LLM budget.
- A single model for all nodes: not chosen because it removes the routing comparison that the benchmark reports (spec §15.6).

## Spec references

AGT-050, AGT-051, C3; spec §3 row 0004.
