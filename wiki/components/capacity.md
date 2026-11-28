# capacity

Status: measured once on 2026-11-27 (W1-T12) without the `shop` workload and without the Rootline services; to be re-measured when `workload` and the services are deployed.

## Purpose

Memory budget of the local cluster: per-pod memory requests measured against the 9.5 GiB limit of success criterion S2 (ARC-030, ARC-031).

## Requirement IDs

ARC-030, ARC-031, S2. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

`task doctor` prints `memory_requests_total` (W1-T06, W1-T12).

## Configuration

Budget table of ARC-030; the sum of requests MUST stay at or below 9.5 GiB. Reduction order when the measured total exceeds it (ARC-031): Prometheus retention 1 d and limit 1 Gi; Loki and Tempo retention 24 h; load-generator users from 10 to 6; `agent` replicas from 2 to 1.

## Measurement 2026-11-27

Command: `kubectl --context k3d-rootline get pods -A -o json`, containers only (init containers and pods in phase `Succeeded` or `Failed` are not counted), the same rule as `memory_requests_gib` in `scripts/doctor.py`. `task doctor` printed `memory_requests_total=3.684 GiB`, limit 9.5 GiB (S2, ARC-030), so no ARC-031 reduction was applied. Cluster state: 13 of 14 ArgoCD Applications Synced/Healthy; Application `workload` could not sync (repository `rootline-env` has no `workload/` path, see [argocd](argocd.md) D4), so namespace `shop` is empty, and the Rootline services are not deployed (week 4 onward). The workload budget of 3.2 GiB (ARC-030) is therefore not measured: namespace `shop` sums to 0 Mi. Applications ran at revision `fix/w1-t12-verify-scratch` (commit `17f2bd6`, see [argocd](argocd.md) "Defects found by W1-T12"), which does not change any resource request.

Per namespace (sum of requests):

| Namespace | Sum of memory requests |
|---|---|
| `argocd` | 640 Mi |
| `cert-manager` | 128 Mi |
| `chaos-mesh` | 256 Mi |
| `cnpg-system` | 96 Mi |
| `external-secrets` | 64 Mi |
| `kube-system` | 140 Mi |
| `kyverno` | 256 Mi |
| `observability` | 1808 Mi |
| `rootline-data` | 384 Mi |
| Total | 3772 Mi = 3.684 GiB |

Per pod (memory request and limit; `-` means unset):

| Namespace | Pod | Memory request | Memory limit |
|---|---|---|---|
| argocd | `argocd-application-controller-0` | 224 Mi | - |
| argocd | `argocd-redis-7fd69749fb-tqnqm` | 64 Mi | - |
| argocd | `argocd-repo-server-747fd44496-ghgjc` | 192 Mi | - |
| argocd | `argocd-server-f449b8b69-jxxrt` | 160 Mi | - |
| cert-manager | `cert-manager-c56c5d58d-j5675` | 48 Mi | - |
| cert-manager | `cert-manager-cainjector-6c694c8586-2hrkm` | 40 Mi | - |
| cert-manager | `cert-manager-webhook-76b789d9c9-6skdk` | 40 Mi | - |
| chaos-mesh | `chaos-controller-manager-86468bdbc7-f2dlh` | 128 Mi | - |
| chaos-mesh | `chaos-daemon-tt8mk` | 96 Mi | - |
| chaos-mesh | `chaos-dns-server-6b69c64db8-66gts` | 32 Mi | - |
| cnpg-system | `cnpg-operator-cloudnative-pg-79cf6dcd99-62rx8` | 96 Mi | 256 Mi |
| external-secrets | `external-secrets-57555dbb5b-44qdd` | 32 Mi | - |
| external-secrets | `external-secrets-cert-controller-8f794f8b4-stpgq` | 16 Mi | - |
| external-secrets | `external-secrets-webhook-58c884df88-k9jkl` | 16 Mi | - |
| kube-system | `coredns-7cfb7bc9c7-82z7d` | 70 Mi | 170 Mi |
| kube-system | `local-path-provisioner-5598c9cb4c-fcxml` | - | - |
| kube-system | `metrics-server-6dc596dfb8-q656j` | 70 Mi | - |
| kube-system | `svclb-traefik-0ee72569-89wpk` | - | - |
| kube-system | `traefik-6bbf99f58-kdbsb` | - | - |
| kyverno | `kyverno-admission-controller-5b75858db4-qzdm9` | 160 Mi | 384 Mi |
| kyverno | `kyverno-background-controller-864bb7f85b-ffh92` | 96 Mi | 128 Mi |
| observability | `alertmanager-observability-kube-prometh-alertmanager-0` | 48 Mi | 128 Mi |
| observability | `loki-0` | 256 Mi | 512 Mi |
| observability | `observability-kube-prometh-operator-697d85fccc-jnqzh` | 96 Mi | 192 Mi |
| observability | `observability-kube-state-metrics-67c6f75c8b-cbxbh` | 64 Mi | 192 Mi |
| observability | `otel-collector-agent-lbf4x` | 192 Mi | 384 Mi |
| observability | `prometheus-observability-kube-prometh-prometheus-0` | 768 Mi | 1536 Mi |
| observability | `tempo-0` | 384 Mi | 768 Mi |
| rootline-data | `rootline-pg-1` | 384 Mi | 768 Mi |

Node memory in use (`kubectl top nodes`) was 6010 Mi (50 %) after about 25 min; WSL reported 11960 Mi total and about 4470 Mi available with Docker and k3d running. Bring-up duration in this measurement was dominated by image pulls (about 2 min per large image on this network).

## Dependencies

A running local cluster (`task up`).

## Data owned

None; the page documents measurements.

## Failure modes and handling

Measured total above 9.5 GiB: apply the ARC-031 steps in order and record each one here.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 297c528 (W1-T12): measured as described in "Measurement 2026-11-27". Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
