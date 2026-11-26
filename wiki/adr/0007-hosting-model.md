# 0007 — Hosting model: no persistent hosting

Status: accepted
Date: 2026-11-26

## Context

Persistent hosting of a GKE cluster would exceed the USD 10 GCP cap, and non-goal NG2 excludes persistent public hosting. The demo therefore exists only while an interview or a test runs.

This decision is row 0007 of the ADR index in spec §3. Primary reason recorded there: Budget.

## Decision

Hosting model: No persistent hosting. Ephemeral Terraform root applied and destroyed per session. Persistent root holds only buckets, the Artifact Registry and state.

Spec §3 row 0007 is the source of this wording. It is implemented by requirement IDs INF-001, S1.

## Consequences

- A demo needs `task gke:up`, which must finish in 25 minutes or less (success criterion S1).
- The persistent Terraform root holds only buckets, the Artifact Registry and state; the ephemeral root is applied and destroyed per session.

## Alternatives considered

- Always-on cluster: not chosen because of the budget (spec §3 reason, GCP cap USD 10 in CST-001).

## Spec references

INF-001, S1; spec §3 row 0007.
