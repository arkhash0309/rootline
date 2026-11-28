# telemetry

Status: names discovered and the metric map written in W1-T13 (branch `feat/w1-baseline-gate`); verified 2026-11-28 in the live k3d cluster `rootline`; alert rules loaded in Prometheus (89 rules, all healthy and inactive).

## Purpose

Records the metric and label names that the telemetry pipeline actually produces, so that the metric mapping in spec §6.5 is expressed in real names (WKL-022), and the alert rules and the baseline health gate built on them (WKL-030 to WKL-032, WKL-004).

## Requirement IDs

WKL-020 to WKL-023, WKL-030 to WKL-032, WKL-004, OBS-001, OBS-002. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`. Decisions: ADR 0049 (`wiki/adr/0049-w1-t13-baseline-gate-decisions.md`), plan gap PG-30.

## Interfaces

### Discovery method (WKL-022)

Verified 2026-11-28, after the first `task up` sync (pod `tempo-0` created 2026-11-28 05:25:10 UTC), with `kubectl --context k3d-rootline -n observability port-forward svc/prometheus-operated 9090` and the Prometheus HTTP API:

| Question | Command | Result |
|---|---|---|
| Span-metrics and service-graph metric names | `curl -s localhost:9090/api/v1/label/__name__/values \| jq -r '.data[]' \| grep -E 'traces_spanmetrics\|traces_service_graph'` | 13 names, table F1 |
| Labels of `traces_spanmetrics_calls_total` | `curl -s 'localhost:9090/api/v1/series?match[]=traces_spanmetrics_calls_total' \| jq '.data[0]'` | `{"__metrics_gen_instance":"tempo-0","__name__":"traces_spanmetrics_calls_total","service":"ad","span_kind":"SPAN_KIND_CLIENT","span_name":"flagd.evaluation.v2.Service/EventStream","status_code":"STATUS_CODE_ERROR"}` |
| JVM GC metric | `grep -Ei 'jvm_gc'` on the metric names | `jvm_gc_duration_seconds_bucket`, `_count`, `_sum` |
| Kafka consumer lag metric | `grep -Ei 'lag'` on the metric names | `kafka_consumer_records_lag`, `kafka_consumer_records_lag_avg`, `kafka_consumer_records_lag_max`, `kafka_lag_max` |

### Findings

| ID | Finding | Used by |
|---|---|---|
| F1 | Tempo metrics-generator (processors `service-graphs`, `span-metrics`) writes these metric names to Prometheus: `traces_spanmetrics_calls_total`, `traces_spanmetrics_latency_bucket`, `traces_spanmetrics_latency_count`, `traces_spanmetrics_latency_sum`, `traces_spanmetrics_size_total`, `traces_service_graph_request_total`, `traces_service_graph_request_failed_total`, `traces_service_graph_request_client_seconds_bucket`, `_count`, `_sum`, `traces_service_graph_request_server_seconds_bucket`, `_count`, `_sum` | `metric-map.yaml` keys `request_rate`, `error_ratio`, `latency_p50`, `latency_p95`, `latency_p99` |
| F2 | Labels of the span-metrics series: `service`, `span_kind`, `span_name`, `status_code`, `__metrics_gen_instance`; `traces_spanmetrics_latency_bucket` adds `le` with the 14 finite bounds `0.002`, `0.004`, `0.008`, `0.016`, `0.032`, `0.064`, `0.128`, `0.256`, `0.512`, `1.024`, `2.048`, `4.096`, `8.192`, `16.384` (seconds) and `+Inf`. `span_kind` values seen: `SPAN_KIND_SERVER`, `SPAN_KIND_CLIENT`, `SPAN_KIND_INTERNAL`, `SPAN_KIND_PRODUCER`, `SPAN_KIND_CONSUMER`. `status_code` values: `STATUS_CODE_UNSET`, `STATUS_CODE_OK`, `STATUS_CODE_ERROR`. The spec §6.5 label names (`service`, `span_kind`, `status_code`) are correct as written | WKL-030 |
| F3 | Service-graph series carry the labels `client` and `server` (for example `client="ad"`, `server="flagd"`) | none in W1 |
| F4 | `service` label values with `SPAN_KIND_SERVER` series (14 of the 19 kept components): `ad`, `cart`, `checkout`, `currency`, `email`, `flagd`, `frontend`, `frontend-proxy`, `image-provider`, `payment`, `product-catalog`, `quote`, `recommendation`, `shipping`. `fraud-detection` has only `SPAN_KIND_CONSUMER` and `SPAN_KIND_CLIENT` series, so its `request_rate` is `0` and its latency series are empty. `astronomy-db`, `kafka`, `valkey-cart` and `load-generator` have no `SPAN_KIND_SERVER` series (`load-generator` has `SPAN_KIND_CLIENT` and `SPAN_KIND_INTERNAL`; the three infrastructure components have no span series) | WKL-004 server-side list, ServiceHighLatency |
| F5 | The `service` label equals the workload (Deployment) name for every kept component: for the OTLP-pushed metrics the labels `service_name` and `k8s_deployment_name` are identical (`ad`/`ad`, `fraud-detection`/`fraud-detection`, `kafka`/`kafka`). So `$svc` equals `$wl` for all 19 kept components, as WKL-030 assumed | `scripts.promql.render` |
| F6 | Pod names of the kept Deployments are `<workload>-<replicaset hash>-<pod hash>`. The spec template regex `pod=~"$wl-.*"` for `$wl=frontend` also matches the pods of `frontend-proxy`. `metric-map.yaml` uses `pod=~"$wl-[a-z0-9]+-[a-z0-9]+"`, which matches exactly the pods of one Deployment (verified 2026-11-28 for `frontend`: the `.*` form sums `0.0859` cores, the exact form `0.0534` cores; the difference is `frontend-proxy`) | `cpu_usage`, `memory_working_set`, `restarts`, baseline gate |
| F7 | `error_ratio` of spec §6.5 answers no data (empty vector) for every service without a `STATUS_CODE_ERROR` series, because `sum()` of an empty selector is empty. The map wraps numerator and denominator in `or vector(0)`: a service without errors answers `0.0`, a service without server spans answers `0.0` | `error_ratio`, baseline gate |
| F8 | Metrics that arrive through the OTLP receiver (JVM and Kafka client metrics) carry `service_name`, `k8s_deployment_name`, `k8s_namespace_name`, `k8s_pod_name`, `job` (`opentelemetry-demo/<service>`) and `instance`, and have no `service` label. The SDK exports one sample per 60 s, so `rate(...[1m])` returns no data; `gc_pause` uses `[5m]`. GC metric: `jvm_gc_duration_seconds_sum` with labels `jvm_gc_action` (`end of minor GC`, `end of major GC`) and `jvm_gc_name` (`Copy`, `MarkSweepCompact`); present for `ad`, `fraud-detection` (and `kafka`, which WKL-030 does not list). Lag metric: `kafka_consumer_records_lag` with labels `client_id` (`consumer-fraud-detection-1`), `partition`, `topic` (`orders`) for `service_name="fraud-detection"`; value `0` at rest | `gc_pause`, `kafka_consumer_lag` |
| F9 | kube-state-metrics series carry `service="observability-kube-state-metrics"` and cAdvisor series carry `service="observability-kube-prometh-kubelet"` (the scraped Service), not the workload name. Alert rules on these series therefore derive `service` with `label_replace` (WKL-031). The render sets memory limits on all 19 Deployments and no CPU limit: `count(kube_pod_container_resource_limits{namespace="shop"}) by (resource)` is `{resource="memory"} 19` and has no `cpu` row, so `HighCPU` is rendered but cannot match until a CPU limit exists. Verified 2026-11-28 with `kubectl -n shop get pods -o json`: 19 containers, 0 with a CPU request or limit. This is an open spec defect, PENDING planner decision (ADR 0049 Consequences): (a) WKL-010 adds CPU limits, then `baseline-v3` and a new gate run; (b) `HighCPU` against an absolute core threshold; (c) `HighCPU` dropped. Catalogue rows C06 and F07 rely on it | `prometheusrule-workload.yaml` |
| F10 | Tempo (`tempo-0`) was OOMKilled 22 times when first measured; at 2026-11-28 17:14 UTC `kubectl --context k3d-rootline -n observability get pod tempo-0 -o jsonpath='{.status.containerStatuses[*].restartCount}'` prints `23` for a pod created at 05:25:10 UTC (11 h 49 min earlier). Container memory limit `768Mi`, `kubectl top` working set `591Mi` (first measurement), last termination reason `OOMKilled`, exit code `137`; the last run lasted 31 min 18 s (`startedAt` 16:21:57 UTC, `finishedAt` 16:53:15 UTC) and the next container started at 16:53:16 UTC (1 s after `finishedAt`). Each restart drops in-flight spans; the duration of the span-metrics gap is unverified (2026-11-28). Prometheus counters from the metrics-generator reset and `rate()` handles that. No workload pod restarted because of it. Open item for the owner (memory budget ARC-030), not changed by W1-T13 | ARC-030 |

### Metric map

`deploy/charts/observability/files/metric-map.yaml` holds the ten WKL-030 keys exactly once (`request_rate`, `error_ratio`, `latency_p50`, `latency_p95`, `latency_p99`, `cpu_usage`, `memory_working_set`, `restarts`, `kafka_consumer_lag`, `gc_pause`) with schema `metrics.<key>: {unit, promql, jvm_only, services}`. The same file is the PromQL source for `scripts/baseline_gate.py`, `templates/prometheusrule-workload.yaml`, mcp-telemetry live mode (W3-T06) and the Fault Lab exporter (W2-T09). All ten templates were evaluated on 2026-11-28 against live Prometheus and answered a value for the services in their `services` field (for `gc_pause` `ad` `0.0` and `fraud-detection` `7.9e-05` seconds per second).

### Alert rules and thresholds

The rules `ServiceHighErrorRate` and `ServiceHighLatency` for `fraud-detection` are rendered (it is one of the 13 `rootlineAlerts.serverServices`) but can never fire, because the service has no `SPAN_KIND_SERVER` series (F4): its `error_ratio` is `0.0` and its latency series are empty. `fraud-detection` is effectively covered by `PodCrashLooping`, `HighMemory` and `KafkaConsumerLagHigh` (and `HighCPU` once CPU limits exist). The baseline gate's `error_ratio` column can never be "no data" (F7: `or vector(0)`), so a service without traffic passes that column; only `restarts` can be "no data".

PrometheusRule `rootline-workload` (namespace `observability`, one group `rootline-workload`) has 89 rules: 13 `ServiceHighErrorRate`, 13 `ServiceHighLatency`, 19 `PodCrashLooping`, 19 `HighCPU`, 19 `HighMemory`, 1 `KafkaConsumerLagHigh`, and one each of `PodNotReady`, `DeploymentReplicasUnavailable`, `ContainerWaiting`, `PodUnschedulable`, `ContainerOOMKilled`. Verified 2026-11-28 in the live cluster (W1-T13 Step 8, branch `feat/w1-baseline-gate` at `77560ca`, Application `root` pointed at that branch): `kubectl -n observability get prometheusrules rootline-workload -o yaml | grep -c "alert:"` prints `89`; Prometheus `/api/v1/rules` lists one group `rootline-workload` with 89 rules, all `health: ok` and `state: inactive`, none with a `lastError`; `/api/v1/alerts` lists no alert with label `rootline="true"`. ExternalSecret `observability/alertmanager-webhook` is `SecretSynced`, Secret `alertmanager-webhook` has the key `token`; the generated Alertmanager configuration has receiver `observability/rootline/rootline-api` with the webhook URL of WKL-032, `send_resolved: true`, `group_by: [alertname, service]`, `group_wait: 30s`, `group_interval: 2m`, `repeat_interval: 1h`, and no `namespace` matcher on the route (`alertmanagerConfigMatcherStrategy.type: None`). Delivery to `api` is not tested: no `api` exists before W4. WKL-032 says "No other receivers"; the live generated configuration (Secret `alertmanager-observability-kube-prometh-alertmanager-generated`, verified 2026-11-28) also has: receiver `null` (kube-prometheus-stack default, no `webhook_configs`), used by the root route (`receiver: "null"`, `group_by: [namespace]`) and by the route for `alertname = "Watchdog"`; the four chart default `inhibit_rules`; `continue: true` on the `rootline` route, forced by the operator; and the receiver name `observability/rootline/rootline-api`. Reading: no other notifying receiver; `null` discards. The inhibit rules have no effect on Rootline alerts: each `alertname` has a single severity (WKL-031) and `equal` includes `alertname`, and no Rootline alert has severity `info`.

Thresholds come from `deploy/values/alert-thresholds.yaml` (byte-identical copy in `deploy/charts/observability/files/`), generated by `scripts/derive_thresholds.py` from the baseline run (see `wiki/components/workload.md` section "Baseline health gate").

## Configuration

Retention: Prometheus 2 d, Loki 48 h, Tempo 48 h locally; 1 d, 24 h, 24 h on GKE (WKL-023). Alertmanager route (WKL-032): `group_by: [alertname, service]`, `group_wait: 30s`, `group_interval: 2m`, `repeat_interval: 1h`, receiver `rootline-api` (`http://api.rootline.svc.cluster.local/hooks/alertmanager`, bearer token from Secret `observability/alertmanager-webhook` key `token`, `sendResolved: true`); `alertmanagerConfigMatcherStrategy.type: None`.

## Dependencies

OTel Collector, Prometheus, Loki, Tempo, kube-state-metrics, External Secrets (generator `password-48` in `observability`).

## Data owned

None; the page documents names only.

## Failure modes and handling

A name in spec §6.5 does not exist in the running stack: record the actual name here and in `metric-map.yaml` (done in W1-T13: findings F6, F7, F8). Tempo restarts (F10): span-metrics gaps of unverified duration (2026-11-28; the container restart itself took 1 s); the baseline gate does not fail because of them.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-28, 77560ca (W1-T13 on branch `feat/w1-baseline-gate`; names and templates verified against the running stack; rule syntax verified by evaluating all 89 expressions through the Prometheus query API, none returned an error).
