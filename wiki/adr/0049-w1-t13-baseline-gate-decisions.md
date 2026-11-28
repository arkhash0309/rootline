# 0049 — Telemetry names, alert rule layout and baseline gate decisions from W1-T13 (spec-gap)

Status: accepted
Date: 2026-11-28
Label: spec-gap
Plan gap: PG-30 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

This ADR holds eight decisions, D1 to D8, taken by the implementer of plan task W1-T13 (`docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T13", branch `feat/w1-baseline-gate`) while it expressed spec §6.5 in the names of the running stack (WKL-022) and built the alert rules and the baseline gate (WKL-004, WKL-030, WKL-031, WKL-032). None of them changes cost, security level or scope; each follows spec §0.3 (simplest, cheapest, safest). The facts they rest on are recorded in `wiki/components/telemetry.md` (findings F1 to F10).

## Context

| ID | Question the documents leave open | Evidence (verified 2026-11-28, k3d cluster `rootline`, context `k3d-rootline`) |
|---|---|---|
| D1 | Which PromQL names and labels do the JVM GC and Kafka lag metrics use, and which label carries the service name? | `jvm_gc_duration_seconds_sum` and `kafka_consumer_records_lag` arrive through the OTLP receiver and carry `service_name`, not `service` (telemetry.md F8) |
| D2 | The WKL-030 pod regex `$wl-.*` for `cpu_usage`, `memory_working_set` and `restarts` | for `$wl=frontend` it also matches the pods of `frontend-proxy`: `0.0859` cores against `0.0534` cores with the exact regex (telemetry.md F6) |
| D3 | The WKL-030 `error_ratio` template answers no data when a service has no error series | `sum()` over an empty selector is an empty vector, so division yields an empty vector: `frontend`, `checkout` and `product-catalog` answered no data before the fix (telemetry.md F7) |
| D4 | The `[1m]` window of `gc_pause` | OTLP-pushed metrics have one sample per 60 s; `rate(jvm_gc_duration_seconds_sum{service_name="ad"}[1m])` is empty, `[5m]` answers `0.0` (telemetry.md F8) |
| D5 | The plan formula uses `numpy.percentile`, but `numpy` is not a dependency of the uv workspace (`pyproject.toml` and `uv.lock` list no `numpy`) | `uv run python -c "import numpy"` fails in the workspace environment |
| D6 | Which services get which alert rule, and how the kube-state-metrics rules obtain the `service` label | WKL-031 says "per service unless noted" and the plan says "one rule per (alert, service)"; kube-state-metrics series already carry `service="observability-kube-state-metrics"` (telemetry.md F9) |
| D7 | Details of the baseline gate: server-side service list, preconditions, how `restarts` and `error_ratio` are computed, what a missing value means | plan Step 4 gives the exclusion list and the two queries but not the pod selector, the subquery step or the no-data rule |
| D8 | Where the Alertmanager webhook Secret and the `AlertmanagerConfig` live, and what the `rootline` namespace copy of the token needs | plan Step 7 mentions an ExternalSecret in `observability` and a copy in `rootline` that W4-T13 creates |

## Decision

**D1 — Names (WKL-022).** `metric-map.yaml` uses these expressions (the full templates are in `deploy/charts/observability/files/metric-map.yaml`):

| Key | Metric and label names |
|---|---|
| `request_rate`, `error_ratio`, `latency_p50`, `latency_p95`, `latency_p99` | `traces_spanmetrics_calls_total` and `traces_spanmetrics_latency_bucket` with `service`, `span_kind="SPAN_KIND_SERVER"`, `status_code="STATUS_CODE_ERROR"` (as spec §6.5) |
| `cpu_usage`, `memory_working_set`, `restarts` | `container_cpu_usage_seconds_total`, `container_memory_working_set_bytes`, `kube_pod_container_status_restarts_total` with `namespace="shop"` and the pod regex of D2 |
| `kafka_consumer_lag` | `sum(kafka_consumer_records_lag{service_name="$svc",k8s_namespace_name="shop"})`, `services: [fraud-detection]`, `jvm_only: false` |
| `gc_pause` | `sum(rate(jvm_gc_duration_seconds_sum{service_name="$svc",k8s_namespace_name="shop"}[5m]))`, `services: [ad, fraud-detection]`, `jvm_only: true` |

`$svc` equals `$wl` for all 19 kept components (telemetry.md F5), so the spec sentence "equal for every kept component unless week 1 discovers otherwise" resolves to "equal".

**D2 — Pod regex.** `$wl-[a-z0-9]+-[a-z0-9]+` replaces `$wl-.*` in `cpu_usage`, `memory_working_set` and `restarts`. The same regex is used by `scripts/baseline_gate.py` (`pod_regex`) and by the `limit` series of `HighCPU` and `HighMemory`.

**D3 — `error_ratio`.** Numerator and denominator are each wrapped as `(sum(...) or vector(0))`; the denominator keeps `clamp_min(..., 1e-9)`. Result: `0.0` for a service without errors or without server spans.

**D4 — `gc_pause` window.** `[5m]` instead of `[1m]` (the minimum that always holds two 60 s samples, with margin for one lost export).

**D5 — Percentile.** `scripts/derive_thresholds.py` implements the percentile in pure Python with linear interpolation (`low + (high - low) * fraction` on the rank `(n - 1) * q / 100`), which equals the default method of `numpy.percentile`. No dependency is added, so `versions.yaml` and `uv.lock` do not change. Test `tests/repo/test_thresholds.py::test_baseline_p95_uses_95th_percentile` asserts `95.05` for the values `1.0` to `100.0`, the value the plan names. Non-finite samples (NaN, `Inf`) are dropped before the percentile; a service without a finite sample gets `baseline_p95 = 0.0`, `ServiceHighLatency = 1.0`, and the lag service gets `KafkaConsumerLagHigh = 1000.0`.

**D6 — Rule layout.** The PrometheusRule `rootline-workload` has one group and 89 rules:

| Alert | Rules | Selector | `service` label |
|---|---|---|---|
| `ServiceHighErrorRate`, `ServiceHighLatency` | 13 each | `rootlineAlerts.serverServices` of `values.yaml` (13 kept server-side services of D7) | static `service: <svc>` |
| `PodCrashLooping`, `HighCPU`, `HighMemory` | 19 each | `rootlineAlerts.workloads` (all 19 kept components, WKL-002) | static |
| `KafkaConsumerLagHigh` | 1 | `rootlineAlerts.kafkaLagService` (`fraud-detection`) | static |
| `PodNotReady`, `DeploymentReplicasUnavailable`, `ContainerWaiting`, `PodUnschedulable`, `ContainerOOMKilled` | 1 each | whole namespace `shop` | none; the expression ends in `label_replace(..., "service", "$1", "pod", "(.*)-[a-z0-9]+-[a-z0-9]+")` (`"deployment", "(.*)"` for `DeploymentReplicasUnavailable`) |

The plan also names the StatefulSet regex `(.*)-[0-9]+`; it is not rendered because the workload render has no StatefulSet (`wiki/components/workload.md` finding (b)), and a second `label_replace` could rewrite a Deployment pod whose hash ends in digits only. `HighCPU` divides `cpu_usage` by `sum(kube_pod_container_resource_limits{resource="cpu",pod=~<D2>})`, `HighMemory` divides `memory_working_set` by the same sum with `resource="memory"`; a workload without a limit series yields an empty vector, which is the "excluded by the limit series" rule of the plan. The render has memory limits on 19 containers and no CPU limit (telemetry.md F9), so the 19 `HighCPU` rules cannot fire until a CPU limit exists. Numbers in thresholds are written with Go `%v` (`1`, `1.5`, `1000`); `for` values and severities equal the WKL-031 table (`tests/repo/test_alert_rules.py::test_every_alert_follows_the_wkl_031_table`).

**D7 — Baseline gate.** `scripts/baseline_gate.py` treats these 13 components as the kept server-side services: `frontend`, `ad`, `cart`, `checkout`, `currency`, `email`, `payment`, `product-catalog`, `quote`, `recommendation`, `shipping`, `fraud-detection`, `image-provider` (`KEPT_COMPONENTS` minus `load-generator`, `frontend-proxy`, `kafka`, `valkey-cart`, `astronomy-db`, `flagd`). Before it starts it checks with `kubectl` that every flag in `ConfigMap/shop/flagd-config` has `defaultVariant: "off"` and that `Deployment/shop/load-generator` has `LOCUST_USERS=10` (WKL-004 "all flags off and load `normal`"); otherwise it exits `2`. `error_ratio` is `avg_over_time((<metric-map error_ratio>)[30m:15s])` at the end time; `restarts` is `sum(increase(kube_pod_container_status_restarts_total{namespace="shop",pod=~<D2>}[30m]))`. A value that does not exist is `FAIL` ("no data"). `fraud-detection` has no server spans, so its `error_ratio` is `0.0` by D3 and it is judged on restarts. `samples.json` and `report.json` go to `data/baseline/<date>/` (directory `data/` is git-ignored); only `deploy/values/alert-thresholds.yaml` and its chart copy are committed.

**D8 — Alertmanager.** `templates/alertmanager-config.yaml` of chart `observability` renders ExternalSecret `observability/alertmanager-webhook` (`refreshInterval: "0"`, `dataFrom` `generatorRef` Password `password-48`, target Secret `alertmanager-webhook` with `type: Opaque` and the single key `token` = `{{ .password }}`) and `AlertmanagerConfig` `observability/rootline` exactly as WKL-032 (route, one receiver `rootline-api`, `sendResolved: true`, `httpConfig.authorization` `type: Bearer` with `credentials` from Secret `alertmanager-webhook` key `token`). `values.yaml` sets `kube-prometheus-stack.alertmanager.alertmanagerSpec.alertmanagerConfigMatcherStrategy: {type: None}`. The `rootline` namespace ExternalSecret and the ClusterSecretStore `observability-reader` are not created in W1-T13: they are W4-T13 (plan Step 7 states the order). The NetworkPolicy `allow-egress-pods` of chart `observability` already allows Alertmanager egress to namespace `rootline`.

## Consequences

- `deploy/charts/observability/files/metric-map.yaml` is the single PromQL source named in the W1-T13 interfaces; W2-T09 and W3-T06 read it unchanged.
- Spec §26 gets one row (PG-30). Spec §6.5 text is not edited: the table keeps the template as written, `metric-map.yaml` holds the finalised form, as WKL-022 and WKL-030 say ("label names finalised per WKL-022").
- `HighCPU` rules exist but are inert until the render gains CPU limits; the owner may decide that later (the render sets memory limits only).
- Telemetry finding F10 (Tempo OOMKilled 22 times in 11 h at its `768Mi` limit) is reported to the coordinator and the owner; this task does not change memory limits, because ARC-030 owns the memory budget.
- The gate result and the thresholds it produced are recorded in `wiki/components/workload.md` section "Baseline health gate".

## Alternatives considered

| Option | Why not |
|---|---|
| Keep `$wl-.*` and accept the `frontend` over-count (D2) | wrong `cpu_usage` for `frontend`, and a false `restarts` hit when `frontend-proxy` restarts |
| Add `numpy` to the workspace (D5) | a new dependency, a `uv.lock` change and a version pin for a ten-line function |
| One cluster-wide rule per alert for `PodCrashLooping`, `HighCPU`, `HighMemory` (D6) | the plan and WKL-031 say per service; per-workload rules reuse the `metric-map.yaml` templates unchanged |
| Create the `rootline` copy of the webhook token now (D8) | the namespace `rootline` has no consumer until W4-T13; the plan assigns it there |
| Scale `latency_p95` thresholds from the gate's own PASS window only | that is what the plan prescribes: thresholds derive from the same 30 minute baseline run |

## Spec references

WKL-004, WKL-022, WKL-030, WKL-031, WKL-032, ARC-030, SEC-100; spec §0.3, §6.2, §6.5, §26.
