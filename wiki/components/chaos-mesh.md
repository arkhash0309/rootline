# chaos-mesh

Status: not implemented yet — planned in W1-T10.

## Purpose

Chaos Mesh (controller, daemon, DNS server), the fault engine for the chaos channel of the Fault Lab (spec §7.3). Installed on `local` only (INF-020 wave -3).

## Requirement IDs

LAB-030, LAB-040, ARC-001, ARC-010, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Chaos custom resources created by `faultlab` in namespace `rootline-lab`; the controller manages namespace `shop` targets.

## Configuration

Namespace `chaos-mesh` with Pod Security level `privileged` because chaos-daemon requires privileges (ARC-010). Memory request 256 Mi total, limit 640 Mi total (ARC-030).

## Dependencies

kube-apiserver; container runtime socket for chaos-daemon.

## Data owned

None.

## Failure modes and handling

Controller down: injected experiments do not start and the Fault Lab preflight check fails (spec §7.5).

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
