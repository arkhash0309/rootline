# workload

Status: render script and transforms implemented in W1-T09 (steps 1 to 5, branch `feat/w1-workload-render`); the real render and the cluster findings below are pending stage W1-S3 (W1-T09 steps 6 and 7).

## Purpose

The trimmed OpenTelemetry Demo (chart `0.42.8`, app `3.1.0`) in namespace `shop`, rendered once into plain YAML in repository `rootline-env` (spec §6).

## Requirement IDs

WKL-001 to WKL-004, WKL-010, WKL-011, WKL-040, WKL-041, GEN-012. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Kept components: WKL-002 (list in `KEPT_COMPONENTS` of `scripts/workload_transforms.py`, 19 names). Disabled components and subcharts: WKL-003 (`deploy/upstream/otel-demo/values.yaml`). Rendering: `uv run python scripts/render_workload.py --out <rootline-env>/workload` runs `helm template shop open-telemetry/opentelemetry-demo --version 0.42.8 --namespace shop -f deploy/upstream/otel-demo/values.yaml`, applies `scripts.workload_transforms.transform`, writes `workload/<component>.yaml`, `workload/flagd-config.yaml`, `workload/networkpolicies.yaml` and `.rootline/baseline.json` (`{"baseline_tag": "baseline-v1", "rendered_from": "0.42.8"}`) next to `workload/`. ArgoCD Application `workload` tracks `main`, path `workload/` of `rootline-env`.

## Configuration

Pod Security level `baseline`, no default-deny NetworkPolicy (ARC-010); `load-generator` `LOCUST_USERS=10`, `LOCUST_SPAWN_RATE=2`, `LOCUST_AUTOSTART=true` (WKL-010 step 7); memory budget at most 3.2 GiB for all kept components (ARC-030). Pending W1-T09 step 6 findings (unverified, 2026-11-27): kind of `astronomy-db` (LAB-011), kind of `valkey-cart` and `kafka`, container index of `LOCUST_USERS` in `load-generator` (WKL-041), env var names in `checkout` and `frontend` used by G02 (LAB-012), every container port per component.

Transform decisions verified by `tests/repo/test_workload_render.py` against the hand-written fixture `tests/repo/fixtures/otel-demo-mini.yaml` (not against a real chart render):

| Transform | Behaviour | Requirement |
|---|---|---|
| Objects of components outside `KEPT_COMPONENTS` | dropped; `Secret` objects always dropped; every kept object gets `metadata.namespace: shop` | WKL-010 steps 1, 2 |
| `OTEL_COLLECTOR_NAME` | set to `otel-collector.observability.svc.cluster.local` wherever present | PG-11, PG-12 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` without `$(OTEL_COLLECTOR_NAME)` | host replaced by the FQDN, scheme and port kept | PG-12 |
| `flagd` | init container `init-config`, sidecar `flagd-ui` and volume `config-ro` removed; volume `config-rw` becomes ConfigMap `flagd-config` | PG-11 |
| `flagd-config` | every flag `defaultVariant` set to `off` | WKL-010 step 6 |
| `load-generator` container 0 | `LOCUST_USERS=10`, `LOCUST_SPAWN_RATE=2`, `LOCUST_AUTOSTART=true` | WKL-010 step 7 |

Unverified (2026-11-27): the ServiceAccount name used by the chart's pods and whether it carries label `app.kubernetes.io/component`; if it carries none, the transform drops it and the pods reference a missing ServiceAccount. Step 6 of W1-T09 (real render) decides this.

## Dependencies

Platform collector and backends in `observability` (WKL-020), `rootline-env` repository.

## Data owned

Stateful components `astronomy-db`, `valkey-cart`, `kafka` (ARC-001).

## Failure modes and handling

Baseline gate (WKL-004) fails: re-enable the missing dependency or disable the load-generator task and record which here. Flag reload fallback (ADR 0033): the flag injector deletes the flagd pod if flagd does not serve the new variant within 120 s.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed (transforms verified by unit tests only; no deployed component exists to verify).
