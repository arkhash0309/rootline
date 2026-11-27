# chaos-mesh

Status: installation configured in W1-T10 (`deploy/upstream/chaos-mesh/values-local.yaml`); not yet deployed to a cluster.

## Purpose

Chaos Mesh (controller, daemon, DNS server), the fault engine for the chaos channel of the Fault Lab (spec §7.3). Installed on `local` only (INF-020 wave -3).

## Requirement IDs

LAB-030, LAB-040, ARC-001, ARC-010, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Chaos custom resources created by `faultlab` in namespace `rootline-lab`; the controller manages namespace `shop` targets.

## Configuration

Namespace `chaos-mesh` with Pod Security level `privileged` because chaos-daemon requires privileges (ARC-010). Application `chaos-mesh` has `envs: [local]` in `deploy/root/values.yaml`, so it is not rendered for `gke` and `ci`; only `values-local.yaml` exists.

| Value | Setting |
|---|---|
| `chaosDaemon.runtime` | `containerd` |
| `chaosDaemon.socketPath` | `/run/k3s/containerd/containerd.sock` |
| `dnsServer.create` | `true` |
| `dashboard.create` | `false` |
| `controllerManager.replicaCount` | `1` |
| Memory requests | controller 128 Mi, daemon 96 Mi, dns 32 Mi (256 Mi total, ARC-030; limits are the chart defaults, none set) |

ARC-030 budget: 256 Mi request, 640 Mi limit in total.

## Dependencies

kube-apiserver; container runtime socket for chaos-daemon.

## Data owned

None.

## Failure modes and handling

Controller down: injected experiments do not start and the Fault Lab preflight check fails (spec §7.5).

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed (stage base): key paths checked against `helm show values chaos-mesh --version 2.8.8`; `tests/repo/test_root_chart.py` passes. Not verified in a cluster (unverified 2026-11-27).
