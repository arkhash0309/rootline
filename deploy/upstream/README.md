# deploy/upstream

Helm values for upstream charts. Layout: `deploy/upstream/<versions.yaml key>/values-<env>.yaml` with `<env>` in
`local`, `ci`, `gke`. The root chart (`deploy/root`) selects the file with the `versionKey` of the Application, passes
it to ArgoCD as `$values/deploy/upstream/<versionKey>/values-<env>.yaml` and ignores a missing file
(`ignoreMissingValueFiles: true`). Chart versions come from `versions.yaml` (GEN-050).

## Source repositories (SEC-110, AppProject `rootline-platform`)

| Chart | `versions.yaml` key | Repository | Used by |
|---|---|---|---|
| `argo-cd` | `argo-cd` | `https://argoproj.github.io/argo-helm` | `task up` (`helm upgrade --install`), not an Application |
| `cert-manager` | `cert-manager` | `https://charts.jetstack.io` | Application `cert-manager` |
| `external-secrets` | `external-secrets` | `https://charts.external-secrets.io` | Application `external-secrets` |
| `cloudnative-pg` | `cloudnative-pg` | `https://cloudnative-pg.github.io/charts` | Application `cnpg-operator` |
| `kyverno` | `kyverno` | `https://kyverno.github.io/kyverno` | Application `kyverno` |
| `chaos-mesh` | `chaos-mesh` | `https://charts.chaos-mesh.org` | Application `chaos-mesh` (local only) |
| `prometheus-operator-crds` | `prometheus-operator-crds` | `https://prometheus-community.github.io/helm-charts` | Application `prometheus-crds` |
| `traefik` | `traefik` | `https://traefik.github.io/charts` | Application `traefik` (gke only; values added in W7) |
| `kube-prometheus-stack` | `kube-prometheus-stack` | `https://prometheus-community.github.io/helm-charts` | dependency of `deploy/charts/observability` (W1-T11) |
| `loki` | `loki` | `https://grafana.github.io/helm-charts` | dependency of `deploy/charts/observability` (W1-T11) |
| `tempo` | `tempo` | `https://grafana.github.io/helm-charts` | dependency of `deploy/charts/observability` (W1-T11) |
| `opentelemetry-collector` | `opentelemetry-collector` | `https://open-telemetry.github.io/opentelemetry-helm-charts` | dependency of `deploy/charts/observability` (W1-T11) |
| Gateway API CRDs (git, not a chart) | `gateway-api` | `https://github.com/kubernetes-sigs/gateway-api` | Application `gateway-api-crds` |
| Rootline repository | none | `git@github.com:arkhash0309/rootline.git` | every local chart and every `$values` reference |

The `rootline-env` repository (`git@github.com:arkhash0309/rootline-env.git`) is the source of Application
`workload` only and belongs to AppProject `rootline-workload`.
