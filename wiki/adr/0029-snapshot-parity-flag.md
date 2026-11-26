# 0029 — Snapshot manifest field `parity`

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-5 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-5 (spec reference MCP-053, LAB-041 step 4): Snapshots captured in week 2 cannot contain `parity/live_outputs.jsonl`: the MCP servers do not exist yet.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-5: `SnapshotManifest` gains `parity: bool`. Week-2 snapshots have `parity: false` and no parity file; they remain valid for evaluation. TST-MCP-010 runs over every snapshot with `parity: true`; W3 acceptance requires ≥ 20 such snapshots. This is a schema addition within `tool_layer_version` "1" because replay ignores the field.

## Consequences

- Week-2 snapshots are valid for evaluation but are not verified by parity.
- W3 acceptance requires at least 20 snapshots with `parity: true`.

## Alternatives considered

- Delay capture to week 3 so that parity files exist: not chosen because it moves the whole capture schedule (PG-5).

## Spec references

PG-5, MCP-053; spec §26 rows PG-5; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
