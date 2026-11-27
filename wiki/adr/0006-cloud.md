# 0006 — Cloud: GCP, zonal GKE Standard, spot nodes, us-central1-a

Status: accepted
Date: 2026-11-26

## Context

The system must run on a managed Kubernetes service for interviews, with the lowest possible bill (GCP cap USD 10, CST-001). Zonal GKE Standard clusters fall under the free zonal management-fee tier, and spot nodes cut node cost. Spec §3 also lists fit with Google as a reason.

This decision is row 0006 of the ADR index in spec §3. Primary reason recorded there: Free zonal management-fee tier; fit with Google.

## Decision

Cloud: GCP, zonal GKE Standard, spot nodes, `us-central1-a`.

Spec §3 row 0006 is the source of this wording. It is implemented by requirement IDs INF-010, C10.

## Consequences

- Spot nodes can be preempted, so the spin-up runbook must tolerate a lost node.
- The zone is `us-central1-a` for every ephemeral cluster.

## Alternatives considered

- AWS EKS: not chosen because the reasons in spec §3 (free zonal management-fee tier, fit with Google) apply to GKE only.
- Azure AKS: not chosen for the same reason.

## Spec references

INF-010, C10; spec §3 row 0006.
