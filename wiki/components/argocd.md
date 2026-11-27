# argocd

Status: configuration implemented in W1-T10 (root chart, values, k3d config); not yet deployed to a cluster.

## Purpose

ArgoCD 3.x, the GitOps controller that applies the platform from `deploy/root` and the workload from `rootline-env` (spec §16.4).

## Requirement IDs

INF-020 to INF-023, SEC-110, GEN-012, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Server port 8080 in namespace `argocd`; public host `argocd.D`. Local accounts `rootline-gate` and `rootline-faultlab` with capability `apiKey` only (SEC-110). AppProjects `rootline-workload` and `rootline-platform` (created in W2-T08; until then every Application uses project `default`).

Root chart `deploy/root` (chart `rootline-root` 0.1.0): one `Application` per enabled entry of `apps` in `deploy/root/values.yaml`, rendered by `deploy/root/templates/apps.yaml` with helpers in `deploy/root/templates/_app.tpl`.

| Wave | Applications (kind) |
|---|---|
| -4 | `namespaces` (local chart), `gateway-api-crds` (git path `config/crd/standard` at tag `v<versions.gateway-api>`) |
| -3 | `cert-manager`, `external-secrets`, `cnpg-operator`, `kyverno`, `prometheus-crds` (upstream charts); `chaos-mesh` (local env only); `traefik` (gke only) |
| -2 | `platform-config` (local chart) |
| -1 | `postgres`, `observability` (local charts, created in W1-T11) |
| 0 | `keycloak`, `argocd-accounts` (disabled until W3 and W2-T08) |
| 1 | `rootline` (umbrella chart) |
| 2 | `workload` (repository `rootline-env`, path `workload`, namespace `shop`), `demo-seed` (disabled; gke only) |

Upstream Applications use two sources: the chart (version `chart` of the `versions.yaml` row, via `deploy/root/files/versions.yaml`) and this repository as `ref: values`, with value file `$values/deploy/upstream/<versionKey>/values-<env>.yaml` (`ignoreMissingValueFiles: true`). The directory is the `versionKey`, not the Application name (Application `cnpg-operator` reads `deploy/upstream/cloudnative-pg/`). Local-chart Applications get the Helm parameters `global.env`, `global.domain`, `global.gcpProject`, `global.k8sIssuer`, `global.artifactsBucket`, `global.ingressIP` and the value files `values.yaml`, `values-<env>.yaml`.

Application `prometheus-crds` carries explicit `repo` and `chartVersion` overrides because `scripts/render_versions.py` (W1-T11 scope) does not yet copy the `prometheus-operator-crds` row into `deploy/root/files/versions.yaml`; `tests/repo/test_root_chart.py::test_application_sources` checks that the overrides equal `versions.yaml`.

## Configuration

No Dex, notifications disabled, ApplicationSet replicas 0; platform Applications use `syncPolicy.automated: {prune: true, selfHeal: true}` and `syncOptions: [CreateNamespace=false, ServerSideApply=true]` (INF-021); `workload` uses `{prune: true, selfHeal: false}` (GEN-012) and an `ignoreDifferences` entry for Deployment `load-generator`, pointer `/spec/template/spec/containers/0/env` (container index 0; the index was not re-checked against W1-T09 step 6(c)).

| Value (`deploy/upstream/argo-cd/values-<env>.yaml`) | Setting |
|---|---|
| `configs.params."server.insecure"` | `true` |
| `configs.cm."admin.enabled"` | `true` |
| `configs.cm."accounts.rootline-gate"`, `"accounts.rootline-faultlab"` | `apiKey` |
| Memory requests | server 160 Mi, repo-server 192 Mi, controller 224 Mi, redis 64 Mi (640 Mi total, ARC-030) |

`values-local.yaml`, `values-ci.yaml` and `values-gke.yaml` have identical content. The k3d cluster is defined in `infra/k3d/rootline.yaml` (INF-030; placeholders `<versions.k3s>` and `<repo>` are substituted by `scripts/up.py`, W1-T12).

## Dependencies

GitHub repositories `rootline` and `rootline-env` (repository Secrets created by `task secrets:local`, ADR 0032).

## Data owned

Application state in the cluster; no persistent store of its own.

## Failure modes and handling

Repository credentials missing or invalid: Applications stay `Unknown`; run `task secrets:local`. Sync failure: the Application shows `OutOfSync` and the recovery runbook applies. `scripts/render_manifests.py` exits 1 when `deploy/root` or a local chart does not render.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

2026-11-27, 908e5ed (stage base): `helm template deploy/root` for `local`, `gke` and `ci`, `helm lint` and `tests/repo/test_root_chart.py` pass. Not verified in a cluster (unverified 2026-11-27).
