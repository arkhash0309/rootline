# otel-collector

Status: chart implemented in W1-T11 (`deploy/charts/observability`, version pinned in `versions.yaml`); deployed on the local k3d cluster in W1-T12 (2026-11-27) with the collector DaemonSet Running and no log-permission error (see "Verified on the cluster").

## Purpose

OpenTelemetry Collector that receives OTLP from the workload and Rootline, adds Kubernetes attributes and exports traces to Tempo, metrics to Prometheus and logs to Loki (spec §6.4).

## Requirement IDs

WKL-020, WKL-021, WKL-022, OBS-001, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

OTLP gRPC port 4317 and OTLP HTTP port 4318 in namespace `observability`, DNS `otel-collector.observability.svc.cluster.local`. Pipelines: WKL-020.

## Configuration

Chart values: `deploy/charts/observability/values.yaml` (key `opentelemetry-collector`); chart `0.183.2`, application `0.165.0`; image `otel/opentelemetry-collector-contrib`, command `otelcol-contrib`. `fullnameOverride: otel-collector` and `service.enabled: true` (the chart creates no Service in `daemonset` mode by default) give the Service `otel-collector` (ports 4317, 4318); the DaemonSet and its ConfigMap are named `otel-collector-agent` (chart naming; spec WKL-020 and ARC-001 name `otel-collector-agent`; ADR 0046 O1). The chart keeps `rewriteDeprecatedComponentNames: true` and `values.yaml` writes the new component names directly (ADR 0046 O2): receivers `otlp` and `file_log`, processors `memory_limiter`, `k8s_attributes`, `batch`, exporters `otlp_grpc/tempo`, `otlp_http/prometheus`, `otlp_http/loki`. The chart-default receivers `jaeger`, `zipkin`, `prometheus` and the exporter `debug` are removed with `null`; the Jaeger and Zipkin container ports are disabled and `otlp` and `otlp-http` have `hostPort: 0`.

Log collection (ADR 0046 O3): the `logsCollection` preset is off (it would also mount `/var/lib/docker/containers`). An explicit `file_log` receiver (`start_at: end`, `include_file_path: true`, container parser, `max_log_size: 102400`) reads `/var/log/pods/shop_*/*/*.log` and `/var/log/pods/rootline_*/*/*.log` through one read-only `hostPath` volume `/var/log/pods` (`type: Directory`). The container runs as UID 0 (the kubelet writes the log files as `root:root` mode `0640`; verified on k3s `v1.36.6+k3s1` on 2026-11-27, see "Verified on the cluster") with all capabilities dropped, `allowPrivilegeEscalation: false`, a read-only root filesystem and the `RuntimeDefault` seccomp profile. PSS `baseline` forbids every `hostPath`, so namespace `observability` is PSS `privileged` with `warn` and `audit` at `baseline` (W1-T10) until the W3-T12 Kyverno policy restores the `baseline` checks. `values-ci.yaml` sets `opentelemetry-collector.enabled: false`.

DaemonSet on k3d (one node), memory request 192 Mi, limit 384 Mi (WKL-020, ARC-030). Pipelines: `traces` = `otlp` to `otlp_grpc/tempo`, `metrics` = `otlp` to `otlp_http/prometheus`, `logs` = `otlp`, `file_log` to `otlp_http/loki`; every pipeline runs `memory_limiter` (80%), `k8s_attributes`, `batch`.

## Verified on the cluster

W1-T12 Step 5, 2026-11-27, k3d `rootline` (k3s `v1.36.6+k3s1`), after the collector pod `otel-collector-agent-lbf4x` had run for more than 5 min. The ArgoCD Applications ran at revision `fix/w1-t12-verify-scratch` (commit `17f2bd6`), which is `develop` at `21ce6fa` plus two root-chart changes that W1-T12 reported as defects (`namespace: observability` for Application `observability` and a `syncPolicy.retry` block, see [argocd](argocd.md) "Defects found by W1-T12"); the observability chart itself was identical to `develop`.

| Check | Command | Output |
|---|---|---|
| Permission errors in the collector log | `kubectl -n observability logs ds/otel-collector-agent \| grep -ci "permission denied"` | `0` |
| Pod log file mode on the node | `docker exec k3d-rootline-server-0 stat -c "%a %U:%G %n" /var/log/pods/*/*/*.log` (first five files) | `640 root:root` for every file |
| Collector container security context | `kubectl -n observability get pod -l component=agent-collector -o jsonpath='{.items[0].spec.containers[0].securityContext}'` | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"readOnlyRootFilesystem":true,"runAsGroup":0,"runAsNonRoot":false,"runAsUser":0,"seccompProfile":{"type":"RuntimeDefault"}}` |

The fallback of ADR 0046 O3 item 3 (`DAC_READ_SEARCH`) was not needed and was not applied. The collector log contains `Starting stanza receiver` for `file_log`.

## Dependencies

Tempo (`tempo.observability.svc:4317`), Prometheus OTLP receiver, Loki OTLP endpoint.

## Data owned

None.

## Failure modes and handling

Backend unreachable: `batch` and `memory_limiter` drop data after the buffer is full; the workload keeps running. Collector down: telemetry gaps appear in snapshots.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 297c528 (W1-T12). `helm template` of the chart `deploy/charts/observability` (`tests/repo/test_observability_values.py`) and the cluster checks in "Verified on the cluster".
