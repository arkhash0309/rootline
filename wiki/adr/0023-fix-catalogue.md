# 0023 — Fix catalogue: six typed actions

Status: accepted
Date: 2026-11-26

## Context

The policy can only reason about actions it can enumerate, so the agent may only propose a fix from a closed catalogue. Feature flags are injected as configuration drift on the live cluster, and the realistic fix for drift is to resynchronise the ArgoCD application.

This decision is row 0023 of the ADR index in spec §3. Primary reason recorded there: Realistic out-of-band changes; actions the policy can reason about.

## Decision

Fix catalogue: Six typed actions (§11.3). Flags are injected as configuration drift and fixed by `resync_app`.

Spec §3 row 0023 is the source of this wording. It is implemented by requirement IDs POL-020.

## Consequences

- Flag faults are fixed by `resync_app`.
- Chaos Mesh faults end with the experiment and the correct action is `none` (NG10).

## Alternatives considered

- Free-form patches: not chosen because spec §3 requires actions that the policy can reason about.
- A `toggle_flag` action: not chosen because flags are injected as out-of-band drift, so the realistic fix is `resync_app`.

## Spec references

POL-020; spec §3 row 0023.
