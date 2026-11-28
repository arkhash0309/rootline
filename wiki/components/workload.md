# workload

Status: baseline gate passed 2026-11-28 (W1-T13). Render script and transforms implemented (W1-T09 steps 1 to 5, amended by ADR 0044). Step 6 (real render and findings) done 2026-11-27. Step 7 done 2026-11-27: `rootline-env` commit `1acc3501b1163ed2e21192a63810b8e7f9898089` (`feat: render workload from opentelemetry-demo 0.42.8`) on `main`, tag `baseline-v1` on that commit, both pushed to origin.

## Purpose

The trimmed OpenTelemetry Demo (chart `0.42.8`, app `3.1.0`) in namespace `shop`, rendered once into plain YAML in repository `rootline-env` (spec §6).

## Requirement IDs

WKL-001 to WKL-004, WKL-010, WKL-011, WKL-040, WKL-041, GEN-012. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Kept components: WKL-002 (list in `KEPT_COMPONENTS` of `scripts/workload_transforms.py`, 19 names). Disabled components and subcharts: WKL-003 (`deploy/upstream/otel-demo/values.yaml`). Rendering: `uv run python scripts/render_workload.py --out <rootline-env>/workload` runs `helm template shop open-telemetry/opentelemetry-demo --version 0.42.8 --namespace shop -f deploy/upstream/otel-demo/values.yaml`, applies `scripts.workload_transforms.transform`, writes `workload/<component>.yaml`, `workload/flagd-config.yaml`, `workload/networkpolicies.yaml` and `.rootline/baseline.json` (`{"baseline_tag": "baseline-v1", "rendered_from": "0.42.8"}`) next to `workload/`. ArgoCD Application `workload` tracks `main`, path `workload/` of `rootline-env`.

## Configuration

Pod Security level `baseline`, no default-deny NetworkPolicy (ARC-010); `load-generator` `LOCUST_USERS=10`, `LOCUST_SPAWN_RATE=2`, `LOCUST_AUTOSTART=true` (WKL-010 step 7); memory budget at most 3.2 GiB for all kept components (ARC-030). The facts of the real render are in section "Render findings" below.

Transform decisions verified by `tests/repo/test_workload_render.py` against the hand-written fixture `tests/repo/fixtures/otel-demo-mini.yaml`, and by the real render in "Render findings":

| Transform | Behaviour | Requirement |
|---|---|---|
| Objects of components outside `KEPT_COMPONENTS` | dropped unless a kept workload references them (rule above); `Secret` objects always dropped; every kept object gets `metadata.namespace: shop` | WKL-010 steps 1, 2, PG-25 |
| `OTEL_COLLECTOR_NAME` | set to `otel-collector.observability.svc.cluster.local` wherever present | PG-11, PG-12 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` without `$(OTEL_COLLECTOR_NAME)` | host replaced by the FQDN, scheme and port kept | PG-12 |
| `flagd` | init container `init-config`, sidecar `flagd-ui` and volume `config-ro` removed; volume `config-rw` becomes ConfigMap `flagd-config` | PG-11 |
| `flagd-config` | every flag `defaultVariant` set to `off` | WKL-010 step 6 |
| `load-generator` container 0 | `LOCUST_USERS=10`, `LOCUST_SPAWN_RATE=2`, `LOCUST_AUTOSTART=true` | WKL-010 step 7 |
| `kafka` container 0 | `KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093` (chart value `1@kafka:9093` made the broker wait for Service `kafka`, which has no endpoint until the pod is Ready; valid only while `kafka` has one replica) | WKL-010 step 7, PG-29, ADR 0048 |

Objects that kept workloads reference (ADR 0044, PG-25). Verified 2026-11-27 by running `scripts/render_workload.py` on chart `0.42.8` with `deploy/upstream/otel-demo/values.yaml` (helm `v3.22.1`, output to a scratch directory, not to `rootline-env`; two runs byte-identical): the render holds 19 Deployments, 18 Services (every kept component except `fraud-detection`), 3 ConfigMaps and 1 ServiceAccount, no Secret and no StatefulSet. ServiceAccount `shop` has no `app.kubernetes.io/component` label and is named by `serviceAccountName: shop` in all 19 Deployments. ConfigMap `postgresql-init` has no component label and is mounted by `astronomy-db`. Rule chosen: an object other than a Secret is kept when (R1) it is ConfigMap `flagd-config`, (R2) its component (label, else name) is in `KEPT_COMPONENTS`, or (R3) it is a ServiceAccount or ConfigMap that a kept workload references; a required reference that resolves to nothing, or to a Secret, makes `transform` raise `UnresolvedReferenceError` and the script exit `3` before it writes anything. Placement: an R3 object with one referring component goes to `workload/<component>.yaml`; with two or more it goes to `workload/serviceaccount.yaml` or `workload/configmaps.yaml`. Result: exactly 22 files: the 19 component files (`fraud-detection.yaml` holds only its Deployment), `flagd-config.yaml`, `networkpolicies.yaml` and `serviceaccount.yaml` (holding `ServiceAccount/shop`); `postgresql-init` is in `astronomy-db.yaml`; no `configmaps.yaml`.

## Render findings

Verified 2026-11-27 (W1-T09 step 6): `uv run python scripts/render_workload.py --out <rootline-env>/workload` on chart `0.42.8` exited `0` twice and the two outputs were byte-identical (WKL-011). It wrote exactly 22 files into `workload/` plus `.rootline/baseline.json`: `ad`, `astronomy-db`, `cart`, `checkout`, `currency`, `email`, `flagd-config`, `flagd`, `fraud-detection`, `frontend-proxy`, `frontend`, `image-provider`, `kafka`, `load-generator`, `networkpolicies`, `payment`, `product-catalog`, `quote`, `recommendation`, `serviceaccount`, `shipping`, `valkey-cart` (each `.yaml`); there is no `configmaps.yaml`. `serviceaccount.yaml` holds one `ServiceAccount`. `astronomy-db.yaml` holds, in order, `ConfigMap`, `Service`, `Deployment`. No finding contradicts the transform.

| Finding | Value | Used by |
|---|---|---|
| (a) kind of `astronomy-db` | `Deployment` (so the entity is `Deployment/shop/astronomy-db`) | LAB-011, F04 |
| (b) kind of `valkey-cart` and `kafka` | both `Deployment`; the render contains no `StatefulSet` | WKL-002, ARC-001 |
| (c) container index of `LOCUST_USERS` in `load-generator` | `0` (the only container, `load-generator`); render value after the transform `10`; `jsonPointers: [/spec/template/spec/containers/0/env]` is correct | WKL-040, WKL-041 |
| (d) G02 env var names | `checkout` container 0: `PAYMENT_ADDR=payment:8080`, `CART_ADDR=cart:8080`, `CURRENCY_ADDR=currency:8080`; `frontend` container 0: `PRODUCT_CATALOG_ADDR=product-catalog:8080`. All four names of spec LAB-012 exist unchanged | LAB-012, G02 |

(e) Container ports, every component has exactly one container (`flagd` after the PG-11 transform) and each port is named:

| Component | Container ports (name: number) |
|---|---|
| `ad` | `prometheus`: 9465, `service`: 8080 |
| `astronomy-db` | `service`: 5432 |
| `cart`, `checkout`, `currency`, `email`, `frontend`, `frontend-proxy`, `payment`, `product-catalog`, `quote`, `recommendation`, `shipping` | `service`: 8080 |
| `flagd` | `rpc`: 8013, `ofrep`: 8016 |
| `fraud-detection` | none (the chart renders no Service and no port) |
| `image-provider` | `service`: 8081 |
| `kafka` | `plaintext`: 9092, `controller`: 9093 |
| `load-generator` | `service`: 8089 |
| `valkey-cart` | `valkey-cart`: 6379 |

Because `fraud-detection` has no port, the readiness probe transform (WKL-010 step 4) adds none to it.

## Baseline health gate

Verified 2026-11-28 (W1-T13 Step 5, WKL-004): `uv run python scripts/baseline_gate.py --minutes 30 --date 2026-11-28` ran from 2026-11-28T16:29:56Z to 16:59:56Z (UTC) against the `baseline-v2` workload (`rootline-env` `b1bd88d`; all 19 Deployments `Running`, Application `workload` `Synced`/`Healthy`), exit code `0`, 0 failed polls. Preconditions checked by the script before the start: every flag in `ConfigMap/shop/flagd-config` has `defaultVariant: "off"` and `Deployment/shop/load-generator` has `LOCUST_USERS=10` (load level `normal`, WKL-040). The first and only run passed, so no dependency was re-enabled, no load-generator task was disabled, and no re-render happened (`BASELINE_TAG` stays `baseline-v2`; `baseline-v3` is not used).

| service | error_ratio (mean over 30 min) | restarts (30 min) | result |
|---|---|---|---|
| `frontend` | 0.000000 | 0.00 | PASS |
| `ad` | 0.000000 | 0.00 | PASS |
| `cart` | 0.000000 | 0.00 | PASS |
| `checkout` | 0.000000 | 0.00 | PASS |
| `currency` | 0.000000 | 0.00 | PASS |
| `email` | 0.000000 | 0.00 | PASS |
| `payment` | 0.000000 | 0.00 | PASS |
| `product-catalog` | 0.000000 | 0.00 | PASS |
| `quote` | 0.000000 | 0.00 | PASS |
| `recommendation` | 0.000000 | 0.00 | PASS |
| `shipping` | 0.000000 | 0.00 | PASS |
| `fraud-detection` | 0.000000 (no server spans, telemetry.md F4) | 0.00 | PASS |
| `image-provider` | 0.000000 | 0.00 | PASS |

Cross-check with an independent query at the end of the run (`sum by (service)(increase(traces_spanmetrics_calls_total{span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[30m]))`): only `flagd` (9.09 errors in 30 min against 20667 server spans) and `frontend-proxy` (1.04 against 30947) have error series; both are outside the 13 gate services (WKL-004 excludes them). The gate input is the metric-map `error_ratio` (telemetry.md F7), the pod selector is `<svc>-[a-z0-9]+-[a-z0-9]+` (telemetry.md F6).

Samples: `data/baseline/2026-11-28/samples.json` (git-ignored directory) holds 115 to 116 points per `latency_p95:<svc>` series for the 12 services with server spans, 0 points for `fraud-detection` and 121 points for `kafka_consumer_lag:fraud-detection` (maximum `0.0`). `scripts/derive_thresholds.py --samples` wrote `deploy/values/alert-thresholds.yaml` and its byte-identical chart copy `deploy/charts/observability/files/alert-thresholds.yaml`. The baseline p95 values (seconds) are `ad` 0.0037, `cart` 0.0025, `checkout` 0.0624, `currency` 0.0019, `email` 0.0272, `fraud-detection` 0.0, `frontend` 0.0419, `image-provider` 0.0019, `payment` 0.0071, `product-catalog` 0.0259, `quote` 0.0019, `recommendation` 0.0133, `shipping` 0.0077. Every `ServiceHighLatency` threshold is the `1.0` s floor (the largest `3 x p95` is `0.1872` s for `checkout`), and `KafkaConsumerLagHigh` is the `1000.0` records floor.

High-load check of `load-generator` (ADR 0049 D9 verification obligation 1, W1-T13 fix round 2): `kubectl --context k3d-rootline -n shop set env deployment/load-generator LOCUST_USERS=20` at 2026-11-28T17:32:24Z (rollout finished 17:32:35Z), kept for 10 min, queried at 17:43:21Z. Highest `cpu_usage` of `load-generator` held for 2 min inside 17:33:21Z to 17:43:21Z: `1.0343` cores (highest raw 1 m value `1.3727` cores); the highest value of any other `shop` pod is `product-catalog` `0.1766`. `1.0343` is below the `HighCPU` threshold `1.5` (telemetry.md F9), so the threshold stays and no `HighCPU` rule fired. `LOCUST_USERS` was set back to `10` at 17:43:25Z; `rollout status deployment/load-generator` exited `0` at 17:43:36Z and the Deployment env reads `LOCUST_USERS=10`. The Application `workload` stayed `Synced` (the `LOCUST_USERS` value is an `ignoreDifferences` pointer of the Application, finding (c)).

Re-running: the gate is read-only against the cluster (kubectl `get` and a Prometheus port-forward). Exit code `1` means at least one row failed; the table names the service. Exit code `2` means a precondition failed (a flag is on, or `LOCUST_USERS` is not `10`) or Prometheus was unreachable.

## Dependencies

Platform collector and backends in `observability` (WKL-020), `rootline-env` repository.

## Data owned

Stateful components `astronomy-db`, `valkey-cart`, `kafka` (ARC-001).

## Failure modes and handling

Baseline gate (WKL-004) fails (it passed on 2026-11-28, section "Baseline health gate"): re-enable the missing dependency or disable the load-generator task and record which here. Flag reload fallback (ADR 0033): the flag injector deletes the flagd pod if flagd does not serve the new variant within 120 s.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-28, 9c6cc4b (W1-T13 on branch `feat/w1-baseline-gate`; baseline health gate run against the live `baseline-v2` workload on k3d; transforms verified earlier by unit tests and two real renders of chart 0.42.8).
