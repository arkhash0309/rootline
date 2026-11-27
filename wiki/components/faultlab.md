# faultlab

Status: not implemented yet — planned in W2-T10.

## Purpose

Fault Lab: generates scenarios, injects faults through feature flags, Chaos Mesh and bad GitOps commits, captures snapshots and labels, then restores the workload (spec §7).

## Requirement IDs

LAB-001, LAB-010 to LAB-013, LAB-020 to LAB-022, LAB-030, LAB-040 to LAB-046, LAB-050 to LAB-052, LAB-060 to LAB-063, LAB-070, LAB-071, SEC-070. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Port 8080 with `/healthz`, `/readyz`, `/metrics`; admin run API (spec §7.5); capture CLI (W2-T10). `/healthz` (liveness, 200 if the process is up), `/readyz` (200 only when the database and every hard dependency are reachable, otherwise 503 with body `{"failing":[...]}`) and `/metrics` (Prometheus exposition; the NetworkPolicy allows only namespace `observability` ingress) (ARC-020).

## Configuration

1 replica; memory request 160 Mi, limit 320 Mi (ARC-030). Container port 8080, ClusterIP Service port 80, DNS `faultlab.rootline.svc.cluster.local` (ARC-020). Container security context per INF-022: `runAsNonRoot: true`, `runAsUser: 10001`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault`.

## Dependencies

kube-apiserver (flags, Chaos Mesh resources), GitHub App `rootline-faultlab`, ArgoCD API (account `rootline-faultlab`), Postgres (role `rootline_faultlab`), telemetry backends.

## Data owned

Schema `lab` (ARC-001, DB-002).

## Failure modes and handling

Preflight check fails: the run does not start (spec §7.5). Injection or capture fails: the run ends `failed` and the workload is restored by ArgoCD sync (spec §7.5). Restore fails: status `restore_failed`, handled by the recovery runbook.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
