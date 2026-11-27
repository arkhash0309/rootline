# otel-collector

Status: not implemented yet — planned in W1-T11.

## Purpose

OpenTelemetry Collector that receives OTLP from the workload and Rootline, adds Kubernetes attributes and exports traces to Tempo, metrics to Prometheus and logs to Loki (spec §6.4).

## Requirement IDs

WKL-020, WKL-021, WKL-022, OBS-001, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

OTLP gRPC port 4317 and OTLP HTTP port 4318 in namespace `observability`, DNS `otel-collector.observability.svc.cluster.local`. Pipelines: WKL-020.

## Configuration

DaemonSet on k3d (one node), processors `memory_limiter` (80%), `k8sattributes`, `batch`; `filelog` include patterns `/var/log/pods/shop_*/*/*.log` and `/var/log/pods/rootline_*/*/*.log`; memory request 192 Mi, limit 384 Mi (WKL-020, ARC-030).

## Dependencies

Tempo (`tempo.observability.svc:4317`), Prometheus OTLP receiver, Loki OTLP endpoint.

## Data owned

None.

## Failure modes and handling

Backend unreachable: `batch` and `memory_limiter` drop data after the buffer is full; the workload keeps running. Collector down: telemetry gaps appear in snapshots.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
