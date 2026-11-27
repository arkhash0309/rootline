# otel-collector

Status: chart implemented in W1-T11 (`deploy/charts/observability`, version pinned in `versions.yaml`); rendered and tested, not yet deployed.

## Purpose

OpenTelemetry Collector that receives OTLP from the workload and Rootline, adds Kubernetes attributes and exports traces to Tempo, metrics to Prometheus and logs to Loki (spec §6.4).

## Requirement IDs

WKL-020, WKL-021, WKL-022, OBS-001, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

OTLP gRPC port 4317 and OTLP HTTP port 4318 in namespace `observability`, DNS `otel-collector.observability.svc.cluster.local`. Pipelines: WKL-020.

## Configuration

Chart values: `deploy/charts/observability/values.yaml` (key `opentelemetry-collector`); chart `0.183.2`, application `0.165.0`; image `otel/opentelemetry-collector-contrib`, command `otelcol-contrib`. `fullnameOverride: otel-collector` and `service.enabled: true` (the chart creates no Service in `daemonset` mode by default) give the Service `otel-collector`; the DaemonSet and ConfigMap are named `otel-collector-agent` (chart naming, so spec WKL-020's "Deployment `otel-collector`" is a DaemonSet in practice; the spec text is not amended). The chart rewrites component ids in the rendered `relay` config to the canonical collector names: `otlp/tempo` becomes `otlp_grpc/tempo`, `otlphttp/*` becomes `otlp_http/*`, `k8sattributes` becomes `k8s_attributes`, `filelog` becomes `file_log`; these are aliases of the spec names with identical behaviour. The `logsCollection` preset mounts `/var/log/pods` read-only from the host and adds an `exclude` for the collector's own log. `values-ci.yaml` sets `opentelemetry-collector.enabled: false`.

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

2026-11-27, 908e5ed. Verified by `helm template` of the chart `deploy/charts/observability` (`tests/repo/test_observability_values.py`, 17 checks plus `helm dependency build`); the stack has not been deployed to a cluster yet (that happens in W1-T12).
