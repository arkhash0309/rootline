# 0030 — Acceptable-action constraints as a typed model

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-6 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-6 (spec reference LAB-050, POL-021): `acceptable_actions: list[ActionSpec]` cannot express constraints such as `replicas ≥ 1` or `memory_limit ≥ baseline`.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-6: Introduce `rootline_schemas.actions.AcceptableAction {type, sha?, workload?, container?, constraints: dict[str, str]}` where each constraint value is `">=<value>"`, `"<=<value>"` or `"==<value>"` and values may be the placeholders `{fault_sha}`, `{target}`, `{baseline_memory_limit}`, `{baseline_cpu_limit}`, resolved at capture into concrete strings. `injected_action` stays an `ActionSpec`.

## Consequences

- A new model `AcceptableAction` is added to `rootline_schemas.actions` in W2-T01.
- `injected_action` stays an `ActionSpec`.

## Alternatives considered

- Encode constraints as strings inside `ActionSpec`: not chosen because `ActionSpec` cannot express constraints such as `replicas >= 1` (PG-6).

## Spec references

PG-6, LAB-050, POL-021; spec §26 rows PG-6; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
