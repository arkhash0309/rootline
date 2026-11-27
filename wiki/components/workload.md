# workload

Status: render script and transforms implemented (W1-T09 steps 1 to 5, amended by ADR 0044). Step 6 (real render and findings) done 2026-11-27. The `rootline-env` commit and tag `baseline-v1` (step 7) are recorded in `wiki/log.md` when made.

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

## Dependencies

Platform collector and backends in `observability` (WKL-020), `rootline-env` repository.

## Data owned

Stateful components `astronomy-db`, `valkey-cart`, `kafka` (ARC-001).

## Failure modes and handling

Baseline gate (WKL-004) fails: re-enable the missing dependency or disable the load-generator task and record which here. Flag reload fallback (ADR 0033): the flag injector deletes the flagd pod if flagd does not serve the new variant within 120 s.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 21ce6fa (transforms verified by unit tests and two real renders of chart 0.42.8; no deployed component exists to verify).
