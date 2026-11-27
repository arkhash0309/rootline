# workload

Status: not implemented yet — planned in W1-T09.

## Purpose

The trimmed OpenTelemetry Demo (chart `0.42.8`, app `3.1.0`) in namespace `shop`, rendered once into plain YAML in repository `rootline-env` (spec §6).

## Requirement IDs

WKL-001 to WKL-004, WKL-010, WKL-011, WKL-040, WKL-041, GEN-012. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Kept components: WKL-002. Disabled components and subcharts: WKL-003. Rendering: `scripts/render_workload.py` (W1-T09). ArgoCD Application `workload` tracks `main`, path `workload/` of `rootline-env`.

## Configuration

Pod Security level `baseline`, no default-deny NetworkPolicy (ARC-010); `load-generator` `LOCUST_USERS=10`, `LOCUST_SPAWN_RATE=2`, `LOCUST_AUTOSTART=true` (WKL-010 step 7); memory budget at most 3.2 GiB for all kept components (ARC-030). This page records the W1-T09 findings: kind of `astronomy-db`, `valkey-cart` and `kafka`, and the container index of `LOCUST_USERS`.

## Dependencies

Platform collector and backends in `observability` (WKL-020), `rootline-env` repository.

## Data owned

Stateful components `astronomy-db`, `valkey-cart`, `kafka` (ARC-001).

## Failure modes and handling

Baseline gate (WKL-004) fails: re-enable the missing dependency or disable the load-generator task and record which here. Flag reload fallback (ADR 0033): the flag injector deletes the flagd pod if flagd does not serve the new variant within 120 s.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
