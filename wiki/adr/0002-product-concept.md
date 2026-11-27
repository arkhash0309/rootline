# 0002 — Product concept: self-diagnosing cluster (AI SRE)

Status: accepted
Date: 2026-11-26

## Context

Rootline is an AI SRE agent that diagnoses incidents in its own Kubernetes cluster and changes production only through policy-checked GitOps pull requests (spec §1.1). The Fault Lab injects faults with known root causes, so every injection yields a labelled scenario without manual annotation (spec §1.2). The concept also makes each required technology (Docker, Kubernetes, GitOps, Terraform, ArgoCD, modern user and agent authentication, Langfuse) do real work that the system would break without (goal G3).

This decision is row 0002 of the ADR index in spec §3. Primary reason recorded there: Free labelled data; every required tool does real work.

## Decision

Product concept: Self-diagnosing cluster (AI SRE).

Spec §3 row 0002 is the source of this wording. It is implemented by requirement IDs §1.2.

## Consequences

- The project needs a live cluster and a Fault Lab (spec §7) from week 2 onward.
- Non-goal NG3 holds: Rootline diagnoses only its own workload in namespace `shop`.

## Alternatives considered

- RAG over documentation: not chosen because it produces no free labelled data and exercises none of the infrastructure technologies of goal G3.
- Coding agent: not chosen because it does not exercise Kubernetes, GitOps, Terraform or ArgoCD (goal G3).

## Spec references

§1.2; spec §3 row 0002.
