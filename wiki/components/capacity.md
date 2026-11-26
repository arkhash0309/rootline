# capacity

Status: not implemented yet — planned in W1-T12.

## Purpose

Memory budget of the local cluster: per-pod memory requests measured against the 9.5 GiB limit of success criterion S2 (ARC-030, ARC-031).

## Requirement IDs

ARC-030, ARC-031, S2. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

`task doctor` prints `memory_requests_total` (W1-T06, W1-T12).

## Configuration

Budget table of ARC-030; the sum of requests MUST stay at or below 9.5 GiB. Reduction order when the measured total exceeds it (ARC-031): Prometheus retention 1 d and limit 1 Gi; Loki and Tempo retention 24 h; load-generator users from 10 to 6; `agent` replicas from 2 to 1.

## Dependencies

A running local cluster (`task up`).

## Data owned

None; the page documents measurements.

## Failure modes and handling

Measured total above 9.5 GiB: apply the ARC-031 steps in order and record each one here.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
