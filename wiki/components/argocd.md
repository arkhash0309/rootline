# argocd

Status: not implemented yet — planned in W1-T10.

## Purpose

ArgoCD 3.x, the GitOps controller that applies the platform from `deploy/root` and the workload from `rootline-env` (spec §16.4).

## Requirement IDs

INF-020 to INF-023, SEC-110, GEN-012, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Server port 8080 in namespace `argocd`; public host `argocd.D`. Local accounts `rootline-gate` and `rootline-faultlab` with capability `apiKey` only (SEC-110). AppProjects `rootline-workload` and `rootline-platform`.

## Configuration

No Dex, notifications disabled, ApplicationSet disabled; platform Applications use `syncPolicy.automated: {prune: true, selfHeal: true}` (INF-021). Memory request 640 Mi total, limit 1.2 Gi total (ARC-030).

## Dependencies

GitHub repositories `rootline` and `rootline-env` (repository Secrets created by `task secrets:local`, ADR 0032).

## Data owned

Application state in the cluster; no persistent store of its own.

## Failure modes and handling

Repository credentials missing or invalid: Applications stay `Unknown`; run `task secrets:local`. Sync failure: the Application shows `OutOfSync` and the recovery runbook applies.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
