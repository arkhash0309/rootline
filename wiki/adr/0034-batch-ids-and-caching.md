# 0034 — Hashed batch custom_id and automatic cache breakpoint

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-14, PG-15 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-14 (spec reference EVL-062): Message Batches `custom_id` must match `^[a-zA-Z0-9_-]{1,64}$`; `"<run_id>:<scenario_id>:<llm_call_seq>"` contains colons and can exceed 64 characters.

PG-15 (spec reference AGT-063): Append-only large-model conversations benefit from caching the growing message prefix, but AGT-063 places a breakpoint only on the last system block.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-14: `custom_id = "c" + sha256("<run_id>:<scenario_id>:<llm_call_seq>").hexdigest()[:48]`. The backend keeps the mapping in memory and appends it to `eval/runs/<run_id>/batch_map.jsonl` (`{custom_id, run_id, scenario_id, seq}`) before submitting, so a resumed sweep can match results.

PG-15: Requests carry the system-block breakpoint (AGT-063) **and** the top-level automatic `cache_control: {"type": "ephemeral"}`, which caches the last cacheable block of the message list. The week-4 cache check (AGT-063) measures the effect.

## Consequences

- `custom_id` is a hashed value and the mapping file `eval/runs/<run_id>/batch_map.jsonl` is written before submission, so a resumed sweep can match results.
- Requests carry an extra top-level `cache_control` breakpoint, and the week-4 cache check measures its effect.

## Alternatives considered

- Truncate the readable identifier to 64 characters: not chosen because truncation cannot guarantee uniqueness (PG-14).
- Cache only the system block (AGT-063 as written): not chosen because the growing message prefix is then not cached (PG-15).

## Spec references

PG-14, PG-15, EVL-062, AGT-063; spec §26 rows PG-14, PG-15; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
