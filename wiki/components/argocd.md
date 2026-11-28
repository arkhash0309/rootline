# argocd

Status: configuration implemented in W1-T10 (root chart, values, k3d config); deployed on the local k3d cluster by `task up` in W1-T12 (2026-11-27); three defects of the root chart and one environment problem were found (see "Defects found by W1-T12").

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

## Defects found by W1-T12

Observed on 2026-11-27 with `task up` on k3d `rootline` (ArgoCD chart `10.20.0`, application `v3.6.3`). W1-T12 does not change the plan or the root chart; the planner decides the fixes (the coordinator received the list in the W1-T12 report). Each fix below was applied on the scratch branch `fix/w1-t12-verify-scratch` (commit `17f2bd6`, not merged) or by a live `kubectl patch`, and the result is listed.

| ID | Symptom | Cause | Tried fix | Result |
|---|---|---|---|---|
| D1 | The `observability` Application deploys Prometheus, Loki, Tempo and the collector into namespace `argocd`; `kubectl -n observability get pods` prints nothing | `deploy/root/values.yaml` entry `observability` has no `namespace` key, and `deploy/root/templates/apps.yaml` falls back to `argocd` for a `local-chart` Application; the subcharts use `.Release.Namespace` | add `namespace: observability` to the entry | Pods Running in `observability`; the Step 5 label checks pass |
| D2 | Application `platform-config` stays `OutOfSync` for good, so the ExternalSecrets `pg-*` never exist and `rootline-pg-1-initdb` fails with `secret "pg-rootline-migrator" not found` | the first sync (wave -2) ran while the External Secrets webhook had no endpoints (`failed calling webhook "validate.clustersecretstore.external-secrets.io"`), and `syncPolicy.automated` without `retry` does not retry a failed sync of the same revision | add `retry: {limit: 5, backoff: {duration: 10s, factor: 2, maxDuration: 3m}}` under `spec.syncPolicy` of every Application in `apps.yaml` | `platform-config` and `postgres` Synced/Healthy after a refresh |
| D3 | Application `root` stays `OutOfSync` with only `Application/kyverno` listed | ArgoCD adds the finalizers `pre-delete-finalizer.argocd.argoproj.io` and `pre-delete-finalizer.argocd.argoproj.io/cleanup` to Application `kyverno` (its chart has a PreDelete hook), and the diff against the rendered `resources-finalizer.argocd.argoproj.io` list does not ignore finalizers | `spec.ignoreDifferences: [{group: argoproj.io, kind: Application, jsonPointers: [/metadata/finalizers]}]` on Application `root` (live patch) | `root` Synced/Healthy |
| D4 | Application `workload` stays `Unknown` with `ComparisonError: workload: app path does not exist` | repository `rootline-env` contains only `README.md`; W1-T09 steps 6 and 7 (real render, commit, tag `baseline-v1`) are deferred to W1-S3 and have not run | none (outside W1-T12) | open; `wait_apps.py` and `task smoke:cluster` report `workload` |

A sync that was started before D1 was fixed stayed `Running` (waiting for DaemonSet `otel-collector-agent` in namespace `argocd`, whose pod Pod Security rejects) and blocked the new revision; `kubectl -n argocd patch application observability --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'` ended it.

Environment problem E1 (this workstation): the WSL file `/etc/resolv.conf` has `search codegen.net`, and the DNS server answers every name below `codegen.net` (wildcard) with `79.72.77.199`. k3s copies the node search list into every pod (`ndots:5`), so the ArgoCD repo-server resolved `github.com` as `github.com.codegen.net` = `79.72.77.199`, `git@github.com:arkhash0309/rootline.git` timed out on port 22 (`failed to list refs: dial tcp 79.72.77.199:22: connect: connection timed out`) and every Application stayed `Unknown`. Workaround used for the verification, not stored in the repository: `docker exec k3d-rootline-server-0 sh -c "grep -v '^search' /etc/resolv.conf > /tmp/r && cat /tmp/r > /etc/resolv.conf"` and `kubectl -n argocd rollout restart` of `argocd-repo-server`, `argocd-server` and `argocd-application-controller`. The setting is lost when the k3d node container is recreated (`task down`, `task up`). A repository-level fix (for example `--kubelet-arg=resolv-conf=` in `infra/k3d/rootline.yaml`) is a decision for the planner.

## Verified on the cluster

2026-11-27: `task up` created the cluster, installed ArgoCD, applied `root` and, after the workarounds above, 13 of the 14 Applications (`root` and 12 children) reached `Synced`/`Healthy`: `cert-manager`, `chaos-mesh`, `cnpg-operator`, `external-secrets`, `gateway-api-crds`, `kyverno`, `namespaces`, `observability`, `platform-config`, `postgres`, `prometheus-crds`, `rootline`. `workload` is the exception (D4). Gateway `kube-system/rootline` (class `traefik`) has `Accepted=True` and `Programmed=True` with address `172.23.0.2`; listeners `http` (8000) and `https` (8443) each report `Accepted=True`, `ResolvedRefs=True`, `Programmed=True` (ADR 0046 T9). The root Application and its children ran at revision `fix/w1-t12-verify-scratch` (commit `17f2bd6`).

## Last verified

2026-11-27, 297c528 (W1-T12): cluster bring-up as above. `helm template deploy/root` for `local`, `gke` and `ci`, `helm lint` and `tests/repo/test_root_chart.py` passed at stage base 908e5ed.
