# 0008 — Autonomy: risk-tiered OPA policy, default-deny

Status: accepted
Date: 2026-11-26

## Context

An agent that can change production must have explicit limits. A policy that classifies every proposal into a tier and denies by default lets the gate merge safe changes automatically and require a human for risky ones. The design shows judgement about autonomy boundaries, which is a hiring signal for the target role (ADR 0001).

This decision is row 0008 of the ADR index in spec §3. Primary reason recorded there: Shows judgement about autonomy boundaries.

## Decision

Autonomy: Risk-tiered OPA policy, default-deny (§11.4).

Spec §3 row 0008 is the source of this wording. It is implemented by requirement IDs POL-030 to POL-032.

## Consequences

- The T0 auto-merge threshold is calibrated by EVL-061 in week 7.
- The policy lives in `policies/opa/` and is evaluated by the OPA sidecar of the gate (spec §11.5).

## Alternatives considered

- Human approval for all proposals: not chosen because it removes the autonomy-boundary judgement that spec §3 names as the reason and the T0 calibration of EVL-061.
- Full autonomy: not chosen because it violates success criterion S5 (no proposal outside T0 merges without a recorded approval).

## Spec references

POL-030 to POL-032; spec §3 row 0008.
