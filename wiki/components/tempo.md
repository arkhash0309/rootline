# tempo

Status: not implemented yet — planned in W1-T11.

## Purpose

Tempo in monolithic mode, the trace store, with the metrics-generator enabled (spec §6.4).

## Requirement IDs

WKL-020, WKL-022, WKL-023, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

HTTP port 3200 and OTLP gRPC port 4317 in namespace `observability`. Metrics-generator processors: `service-graphs` and `span-metrics`, remote-writing to Prometheus.

## Configuration

Retention 48 h locally and 24 h on GKE; memory request 384 Mi, limit 768 Mi (WKL-023, ARC-030).

## Dependencies

OTel Collector (writer), Prometheus (remote-write target).

## Data owned

Trace blocks with the retention above.

## Failure modes and handling

Tempo down: traces are dropped by the collector and span-derived metrics stop.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
