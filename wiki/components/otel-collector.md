# otel-collector

Status: chart implemented in W1-T11 (`deploy/charts/observability`, version pinned in `versions.yaml`); rendered and tested, not yet deployed.

## Purpose

OpenTelemetry Collector that receives OTLP from the workload and Rootline, adds Kubernetes attributes and exports traces to Tempo, metrics to Prometheus and logs to Loki (spec §6.4).

## Requirement IDs

WKL-020, WKL-021, WKL-022, OBS-001, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

OTLP gRPC port 4317 and OTLP HTTP port 4318 in namespace `observability`, DNS `otel-collector.observability.svc.cluster.local`. Pipelines: WKL-020.

## Configuration

Chart values: `deploy/charts/observability/values.yaml` (key `opentelemetry-collector`); chart `0.183.2`, application `0.165.0`; image `otel/opentelemetry-collector-contrib`, command `otelcol-contrib`. `fullnameOverride: otel-collector` and `service.enabled: true` (the chart creates no Service in `daemonset` mode by default) give the Service `otel-collector` (ports 4317, 4318); the DaemonSet and its ConfigMap are named `otel-collector-agent` (chart naming; spec WKL-020 and ARC-001 name `otel-collector-agent`; ADR 0046 O1). The chart keeps `rewriteDeprecatedComponentNames: true` and `values.yaml` writes the new component names directly (ADR 0046 O2): receivers `otlp` and `file_log`, processors `memory_limiter`, `k8s_attributes`, `batch`, exporters `otlp_grpc/tempo`, `otlp_http/prometheus`, `otlp_http/loki`. The chart-default receivers `jaeger`, `zipkin`, `prometheus` and the exporter `debug` are removed with `null`; the Jaeger and Zipkin container ports are disabled and `otlp` and `otlp-http` have `hostPort: 0`.

Log collection (ADR 0046 O3): the `logsCollection` preset is off (it would also mount `/var/lib/docker/containers`). An explicit `file_log` receiver (`start_at: end`, `include_file_path: true`, container parser, `max_log_size: 102400`) reads `/var/log/pods/shop_*/*/*.log` and `/var/log/pods/rootline_*/*/*.log` through one read-only `hostPath` volume `/var/log/pods` (`type: Directory`). The container runs as UID 0 (the kubelet writes the log files as `root:root` mode `0640`; unverified on k3s on 2026-11-27, W1-T12 Step 5 verifies it) with all capabilities dropped, `allowPrivilegeEscalation: false`, a read-only root filesystem and the `RuntimeDefault` seccomp profile. PSS `baseline` forbids every `hostPath`, so namespace `observability` is PSS `privileged` with `warn` and `audit` at `baseline` (W1-T10) until the W3-T12 Kyverno policy restores the `baseline` checks. `values-ci.yaml` sets `opentelemetry-collector.enabled: false`.

DaemonSet on k3d (one node), memory request 192 Mi, limit 384 Mi (WKL-020, ARC-030). Pipelines: `traces` = `otlp` to `otlp_grpc/tempo`, `metrics` = `otlp` to `otlp_http/prometheus`, `logs` = `otlp`, `file_log` to `otlp_http/loki`; every pipeline runs `memory_limiter` (80%), `k8s_attributes`, `batch`.

## Dependencies

Tempo (`tempo.observability.svc:4317`), Prometheus OTLP receiver, Loki OTLP endpoint.

## Data owned

None.

## Failure modes and handling

Backend unreachable: `batch` and `memory_limiter` drop data after the buffer is full; the workload keeps running. Collector down: telemetry gaps appear in snapshots.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed. Verified by `helm template` of the chart `deploy/charts/observability` (`tests/repo/test_observability_values.py`, 24 checks plus `helm dependency build`); the stack has not been deployed to a cluster yet (that happens in W1-T12).
