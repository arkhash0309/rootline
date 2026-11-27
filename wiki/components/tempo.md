# tempo

Status: chart implemented in W1-T11 (`deploy/charts/observability`, version pinned in `versions.yaml`); rendered and tested, not yet deployed.

## Purpose

Tempo in monolithic mode, the trace store, with the metrics-generator enabled (spec §6.4).

## Requirement IDs

WKL-020, WKL-022, WKL-023, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

HTTP port 3200 and OTLP gRPC port 4317 in namespace `observability`. Metrics-generator processors: `service-graphs` and `span-metrics`, remote-writing to Prometheus.

## Configuration

Chart values: `deploy/charts/observability/values.yaml` (key `tempo`); chart `1.24.4`, application `2.9.0`. `fullnameOverride: tempo` makes the Service `tempo` (DNS `tempo.observability.svc`). `tempo.metricsGenerator.enabled: true` with `remoteWriteUrl: http://prometheus-operated.observability.svc:9090/api/v1/write` and `tempo.overrides.defaults.metrics_generator.processors: [service-graphs, span-metrics]` (rendered under `overrides.defaults` of `tempo.yaml`). The chart keeps its default Jaeger and OpenCensus receivers because its Service template requires the Jaeger ports. Usage reporting is off. `values-gke.yaml` sets `retention: 24h`; `values-ci.yaml` sets `tempo.enabled: false`. The metric and label names produced by the generator are recorded in `wiki/components/telemetry.md` by W1-T13 (WKL-022).

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

2026-11-27, 908e5ed. Verified by `helm template` of the chart `deploy/charts/observability` (`tests/repo/test_observability_values.py`, 17 checks plus `helm dependency build`); the stack has not been deployed to a cluster yet (that happens in W1-T12).
