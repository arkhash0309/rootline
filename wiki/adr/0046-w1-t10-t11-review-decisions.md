# 0046 — GitOps root and observability decisions from the W1-T10 and W1-T11 reviews (spec-gap)

Status: accepted (decision O3 waits for the owner's confirmation, see "Owner confirmation")
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-27 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

This is one ADR with sixteen decisions. T1 to T11 answer the review of W1-T10 (branch `feat/w1-gitops-root` at `2bc66d5`, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T10"). O1 to O5 answer the review of W1-T11 (branch `feat/w1-observability-postgres` at `c35124d`, plan "Task W1-T11"). Both tasks are in the parallel stage W1-P3.

## Context

The two reviews found plan text that the implementers could not follow literally, values the plan did not pin, and two defects that would stop the local cluster from working:

- **T9 (defect).** Traefik binds a Gateway listener to the entry point whose port equals the listener port. The Traefik entry points are `web` `:8000` and `websecure` `:8443`, so the plan's listeners on 80 and 443 never become ready, and no route served by Gateway `rootline` would work. The plan's HelmChartConfig key `ports.websecure.tls.enabled` is also rejected by the schema of upstream charts `40.1.0` and `43.0.0`.
- **O3 (defect).** The `logsCollection` preset of chart `opentelemetry-collector` `0.183.2` adds `hostPath` volumes `/var/log/pods` and `/var/lib/docker/containers`. Namespace `observability` is PSS `baseline` (ARC-010), and `baseline` forbids every `hostPath` volume, so Pod Security admission rejects every collector pod.

The other fourteen items are gaps: an ordering between two parallel tasks (T1), template text that differs from the implemented and correct behaviour (T2, T3, O1, O2), choices made by the implementers that no document records (T4, T5, T7, T8, T10, O4, O5), a generated file that nothing ignores (T6), and one value copied by hand into a second file (T11).

## Verification performed on 2026-11-27

All commands ran in WSL Ubuntu 26.04 with helm `v3.22.1`.

| Fact | How it was verified |
|---|---|
| k3s `v1.36.6+k3s1` (`versions.yaml` key `k3s`) installs the bundled Traefik from chart `traefik-40.1.7+up40.1.0.tgz` (Rancher repack of upstream chart `40.1.0`, app `v3.7.1`, image overridden to `rancher/mirrored-library-traefik:3.7.15`) | `curl -sfL https://raw.githubusercontent.com/k3s-io/k3s/v1.36.6%2Bk3s1/manifests/traefik.yaml` (HelmChart `kube-system/traefik`, `spec.chart` and `valuesContent`) |
| The Rancher repack has no `values.schema.json`, so on k3s the key `ports.websecure.tls` is ignored without an error; upstream `40.1.0` and `43.0.0` reject it: `at '/ports/websecure': additional properties 'tls' not allowed` | `helm template` of `k3s-io/k3s-charts` `assets/traefik/traefik-40.1.7+up40.1.0.tgz`, of `traefik/traefik` `40.1.0` and of `traefik/traefik` `43.0.0`, each with the k3s `valuesContent` plus the W1-T10 HelmChartConfig values |
| In all three charts (k3s values, `deployment.replicas: 1`, `providers.kubernetesGateway.enabled: true`, `ports.websecure.http.tls.enabled: true`): container ports `web` 8000 and `websecure` 8443; args `--entryPoints.web.address=:8000/tcp`, `--entryPoints.websecure.address=:8443/tcp`, `--entryPoints.websecure.http.tls=true`, `--providers.kubernetesgateway`, `--providers.kubernetesgateway.statusaddress.service.name=traefik`; Service `traefik` ports `web` 80 → `targetPort: web` and `websecure` 443 → `targetPort: websecure`; GatewayClass `traefik` (controller `traefik.io/gateway-controller`) | same `helm template` runs |
| With chart default `gateway.enabled: true` every chart also renders `Gateway traefik-gateway` in the release namespace with one listener `web` port 8000, `protocol: HTTP`; with `gateway.enabled: false` it renders no Gateway and still renders GatewayClass `traefik` | same `helm template` runs, with and without `gateway: {enabled: false}` |
| Chart `opentelemetry-collector` `0.183.2` (app `0.165.0`) with `fullnameOverride: otel-collector`, `mode: daemonset`, `service.enabled: true` renders DaemonSet `otel-collector-agent`, ConfigMap `otel-collector-agent`, Service `otel-collector` (ports 4317 `otlp`, 4318 `otlp-http`), ServiceAccount, ClusterRole and ClusterRoleBinding `otel-collector`; pod labels `app.kubernetes.io/name: opentelemetry-collector`, `app.kubernetes.io/instance: <release>`, `component: agent-collector` | `helm template observability opentelemetry-collector-0.183.2.tgz` with the `opentelemetry-collector` block of `feat/w1-observability-postgres` `deploy/charts/observability/values.yaml` |
| Chart default `rewriteDeprecatedComponentNames: true` renames, in the rendered config and in every pipeline list, `filelog` → `file_log`, `k8sattributes` → `k8s_attributes`, `otlp/<name>` exporters → `otlp_grpc/<name>`, `otlphttp/<name>` → `otlp_http/<name>`; receivers `otlp`, processors `memory_limiter` and `batch` keep their names | same run; `templates/_config.tpl` `opentelemetry-collector.rewriteDeprecatedComponentNames` |
| With `presets.logsCollection.enabled: false`, an explicit `file_log` receiver, `extraVolumes`/`extraVolumeMounts` for `/var/log/pods` and the `securityContext` of O3, the DaemonSet has exactly two volumes: the config ConfigMap and `hostPath: {path: /var/log/pods, type: Directory}` mounted read-only; the rendered config lists receivers `file_log`, `otlp`, processors `batch`, `k8s_attributes`, `memory_limiter`, exporters `otlp_grpc/tempo`, `otlp_http/loki`, `otlp_http/prometheus` and no `jaeger`, `zipkin`, `prometheus` receiver or `debug` exporter | `helm template` of the same chart with the O3 values block |
| Chart `kube-prometheus-stack` `94.1.0`: operator pods carry `app.kubernetes.io/name: kube-prometheus-stack-prometheus-operator` and listen on container port 10250 `https` (admission webhook, Service port 443); with the four `kube*` components of O5 disabled, the chart renders no Service or ServiceMonitor for them, while ServiceMonitors `kubelet`, `apiserver` and `coredns` remain | `helm template observability kube-prometheus-stack-94.1.0.tgz` with the `kube-prometheus-stack` block of `feat/w1-observability-postgres` and the O5 keys |

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). Only O3 changes a security level; it is marked for owner confirmation. No decision changes cost or scope.

### T1 — Order of the `prometheus-operator-crds` key between W1-T11 and W1-T10

`scripts/render_versions.py` (owned by W1-T11) copies only the keys in `CHART_KEYS` into `deploy/root/files/versions.yaml`, and `prometheus-operator-crds` is not in that list on `develop`. W1-T10 worked around it with per-Application overrides `repo` and `chartVersion` on Application `prometheus-crds`. The overrides are removed, in this order:

1. **W1-T11 (fix round on `feat/w1-observability-postgres`, before its `APPROVE`).** `CHART_KEYS` gains `"prometheus-operator-crds"` directly after `"kube-prometheus-stack"`. The implementer runs `uv run python scripts/render_versions.py` and commits the regenerated `deploy/root/files/versions.yaml` (an always-allowed generated path, overview §7.4) in the same commit. `uv run python scripts/render_versions.py --check` exits 0 on the branch.
2. **Merge order.** The W1-P3 task order in `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml` (and in the W1 "Execution schedule" table) becomes W1-T09, W1-T11, W1-T10, W1-T14. Overview §7.6 step 2 merges in schedule order, so W1-T11 reaches `integration/w1-p3` before W1-T10.
3. **W1-T10 (post-W1-T11 rebase, after W1-T11 is merged into `integration/w1-p3` and before W1-T10 is merged).** The coordinator dispatches the W1-T10 implementer with `mode: resolve-conflict` and the task "W1-P3 integration step 3" (W1 plan, "W1-P3 integration steps"). The implementer rebases `feat/w1-gitops-root` onto `origin/integration/w1-p3`, then on that branch: removes `repo: https://prometheus-community.github.io/helm-charts` and `chartVersion: "33.0.2"` from `apps.prometheus-crds` in `deploy/root/values.yaml` and the comment that explains them; changes the `upstream` branch of `deploy/root/templates/apps.yaml` to read only the `versions.yaml` row (T2 shows the final text); applies T8 and T11; runs `uv run python scripts/render_versions.py` (expected: it writes `deploy/charts/platform-config/files/versions.yaml`, T11, and leaves `deploy/root/files/versions.yaml` unchanged); commits; and force-pushes. Then the reviewer re-reviews only the diff between the approved commit and the new branch tip (`git range-diff`), and the coordinator merges.
4. After step 3, `apps.prometheus-crds` in `deploy/root/values.yaml` is exactly `{enabled: true, wave: -3, kind: upstream, versionKey: prometheus-operator-crds, chart: prometheus-operator-crds, namespace: observability}`, and the rendered Application has `sources[0].repoURL: https://prometheus-community.github.io/helm-charts`, `chart: prometheus-operator-crds`, `targetRevision: "33.0.2"`, all read from `deploy/root/files/versions.yaml`.

### T2 — Values path of an `upstream` Application

The values file of an `upstream` Application is `$values/deploy/upstream/<versionKey>/values-<env>.yaml`, not `$values/deploy/upstream/<Application name>/…`. The two differ for Application `cnpg-operator` (`versionKey: cloudnative-pg`, values in `deploy/upstream/cloudnative-pg/`) and Application `prometheus-crds` (`versionKey: prometheus-operator-crds`; no values file, `ignoreMissingValueFiles: true`). The directory names of W1-T10 Step 7 already use the `versions.yaml` key. The final `upstream` branch of `deploy/root/templates/apps.yaml` is:

```yaml
  {{- else if eq $app.kind "upstream" }}
  {{- $v := required (printf "deploy/root/files/versions.yaml has no key %s" $app.versionKey) (index $versions $app.versionKey) }}
  sources:
    - repoURL: {{ $v.repo }}
      chart: {{ $app.chart }}
      targetRevision: {{ $v.chart | quote }}
      helm:
        valueFiles:
          - $values/deploy/upstream/{{ $app.versionKey }}/values-{{ $.Values.env }}.yaml
        ignoreMissingValueFiles: true
    - repoURL: {{ $.Values.repoURL }}
      targetRevision: {{ $.Values.targetRevision }}
      ref: values
```

A missing key makes `helm template` fail with `deploy/root/files/versions.yaml has no key <key>`; there is no default. Until step 3 of T1, `feat/w1-gitops-root` keeps its current `| default dict` and override lines.

### T3 — `gateway-api` revision

`versions.yaml` holds `gateway-api: "1.7.0"` (a scalar, W1-T02), and the `kubernetes-sigs/gateway-api` Git tags carry a `v` prefix. The `url` branch of `apps.yaml` therefore renders `targetRevision: v{{ $v }}` (`v1.7.0`), where `$v` is the scalar; the plan text `{{ $v.version }}` was wrong.

### T4 — Namespaces of the ESO `Password` generators

An ExternalSecret's `generatorRef` to kind `Password` is resolved in the ExternalSecret's own namespace. `deploy/charts/platform-config/values.yaml` key `generatorNamespaces: [rootline-data, rootline, keycloak, observability]` renders both generators (`password-48`, `password-43`) into each of these four namespaces (8 objects). They are exactly the namespaces whose SEC-100 Secrets are generated: `rootline-data` (DB role secrets, PG-10), `rootline` (`alertmanager-webhook` copy, `job-token-key`, `bff-session-key`, `bff-client-secret`), `keycloak` (`keycloak-admin`, `bff-client-secret`) and `observability` (`alertmanager-webhook`). A task that adds a generated Secret in another namespace adds that namespace to the list in the same PR.

Rejected: one cluster-scoped `ClusterGenerator` (`generators.external-secrets.io/v1alpha1`) per length. It would let an ExternalSecret in any namespace, `shop` included, generate secrets; it uses a different spec shape (`spec.kind: Password` plus `spec.generator.passwordSpec`), so the tested objects and W1-T10 tests would change; and eight namespaced objects cost nothing.

### T5 — `copy-ca` and ConfigMap `rootline-ca` only on `local` and `ci`

`deploy/charts/platform-config/templates/ca-configmap.yaml` renders the `copy-ca` Job, its RBAC and ConfigMap `copy-ca-kustomization` only when `global.env` is `local` or `ci`, because the Job reads secret `cert-manager/rootline-local-ca`, which only `ca.yaml` creates, and `ca.yaml` renders on `local` and `ci` only. On `gke`, ConfigMap `rootline-ca` (namespaces `rootline` and `keycloak`, key `ca.crt`, SEC-011) is added by **W7-T02 Step 3** (INF-041):

1. Default (`tls.issuer` unset or `letsencrypt-prod`): `deploy/charts/platform-config/templates/letsencrypt.yaml` renders ConfigMap `rootline-ca` in `rootline` and in `keycloak`, key `ca.crt` = the content of `deploy/charts/platform-config/files/letsencrypt-roots.pem`. That file holds, concatenated in PEM, every root certificate that https://letsencrypt.org/certificates/ lists as active on the W7-T02 implementation date; W7-T02 downloads each from that page, records each certificate's subject and SHA-256 fingerprint in `wiki/components/cert-manager.md`, and commits the file.
2. Fallback (`tls.issuer=rootline-ca`, INF-041): `ca.yaml` and `ca-configmap.yaml` also render on `gke` (condition `or (has .Values.global.env (list "local" "ci")) (eq ((.Values.tls).issuer) "rootline-ca")`), and `letsencrypt.yaml` does not render its ConfigMap.
3. The W7-T02 `owns` list in the schedule YAML gains `deploy/charts/platform-config/templates/ca.yaml`, `deploy/charts/platform-config/templates/ca-configmap.yaml` and `deploy/charts/platform-config/files/letsencrypt-roots.pem`.

### T6 — `infra/k3d/rootline.generated.yaml` is ignored by git

`infra/k3d/rootline.yaml` keeps the two INF-030 placeholders literally: `image: rancher/k3s:<versions.k3s>` and `<repo>` in the volume. `scripts/up.py` (W1-T12 Step 3 item 1) writes the substituted file `infra/k3d/rootline.generated.yaml`. **W1-T12** adds to `.gitignore`, at the end of the file, the two lines `# Generated k3d config (W1-T12, ADR 0046 T6)` and `infra/k3d/rootline.generated.yaml`. W1-T12 is in the sequential stage W1-S3, which has no `owns` list (overview §7.4), and its "Files" list gains `Modify: .gitignore`. W1-T10 does not touch `.gitignore`.

### T7 — CPU requests are not set in W1

ARC-030 budgets memory only. The values written by W1-T10 (upstream charts, Step 7) and W1-T11 (observability, Postgres) set memory requests and limits and no CPU request or limit. SEC-090 `require-resources` (CPU and memory requests plus a memory limit, in `rootline*` namespaces) is enforced from **W3-T12**. The only W1 pods in a `rootline*` namespace are the CNPG pods of Cluster `rootline-pg` in `rootline-data` (instance pod and the CNPG initdb Job, which use the Cluster's `spec.resources`). W3-T12 therefore sets `resources.requests.cpu: 100m` (no CPU limit) in `deploy/charts/postgres/templates/cluster.yaml`, and its `owns` list gains that path. CPU values for Rootline services are set by the tasks that deploy them, before W3-T12 enforces the policy.

### T8 — `scripts/render_manifests.py --allow-missing`

1. Default behaviour (unchanged): a `local-chart` Application whose `path` has no `Chart.yaml` makes the script print `render_manifests: chart not found: <path>` on stderr and exit 1.
2. Until the end of W1-P3, the script also accepts `--allow-missing`: a missing chart directory prints `skip <env> <name>: <path> not present` on stderr and is skipped; every other failure still exits 1. `tests/repo/test_root_chart.py::test_render_manifests_script` passes `--allow-missing`, because `deploy/charts/postgres` and `deploy/charts/observability` (W1-T11) do not exist on `feat/w1-gitops-root` before T1 step 3.
3. In T1 step 3 (W1-T10, after W1-T11 is in `integration/w1-p3`), the implementer removes the flag: the `--allow-missing` argument, the skip branch and the docstring paragraph go from `scripts/render_manifests.py`; `test_render_manifests_script` runs the script without arguments and still expects exit 0; `test_render_manifests_missing_chart_fails` is unchanged. No commit that reaches `develop` contains the flag.

### T9 — Gateway listener ports, the default Traefik Gateway and the HelmChartConfig keys

1. `deploy/charts/platform-config/templates/gateway.yaml`: Gateway `rootline` (namespace `kube-system` on `local` and `ci`, `traefik` on `gke`, `gatewayClassName: traefik`) has listener `http` with `port: 8000`, `protocol: HTTP`, and listener `https` with `port: 8443`, `protocol: HTTPS`, `tls: {mode: Terminate, certificateRefs: [{name: rootline-wildcard-tls}]}`; both keep `allowedRoutes: {namespaces: {from: All}}`. A Gateway API listener port is the Traefik entry point port, not the port the client uses.
2. Clients still use 80 and 443. Local path: browser → `127.0.0.1:443` → k3d load balancer (`443:443`, INF-030) → k3s ServiceLB pod of Service `kube-system/traefik` → Service port 443 `websecure` → `targetPort: websecure` = container port 8443 → entry point `websecure` (`:8443/tcp`) → listener `https` 8443. Port 80 maps the same way to 8000 and listener `http`. In-cluster callers resolve `auth.D`, `console.D`, `argocd.D` to `traefik.kube-system.svc.cluster.local` (SEC-011, `coredns-custom`) and connect to Service port 443, which reaches the same 8443. On `gke` the upstream chart `43.0.0` has the same Service-to-container mapping (verified above), with `service.type: LoadBalancer`. The Gateway's status address is the Service's address (`--providers.kubernetesgateway.statusaddress.service.name=traefik`).
3. Every HTTPRoute `parentRefs` entry that names a port MUST use 8000 or 8443; plans attach routes by `sectionName` (`http`, `https`) or by Gateway name only, which needs no change.
4. The chart-default Gateway `traefik-gateway` is disabled with `gateway.enabled: false`: Rootline uses one Gateway, `rootline`, and `traefik-gateway` (listener `web` 8000, routes from its own namespace only) would be an unused second Gateway on the same entry point. GatewayClass `traefik` is still created by the chart.
5. The key that enables TLS on entry point `websecure` is `ports.websecure.http.tls.enabled` (already `true` by chart default); `ports.websecure.tls.enabled` is not a chart key. `infra/k3d/manifests/traefik-config.yaml` `valuesContent` becomes exactly:

```yaml
deployment:
  replicas: 1
gateway:
  enabled: false
providers:
  kubernetesGateway:
    enabled: true
ports:
  websecure:
    http:
      tls:
        enabled: true
```

6. The same two keys (`gateway.enabled: false`, `ports.websecure.http.tls.enabled: true`) replace `ports.websecure.tls.enabled: true` in the GKE Traefik values (W7-T02 Step 2, `deploy/upstream/traefik/values-gke.yaml`) and are added to the kind Traefik values (W6-T09 Step 2, `deploy/upstream/traefik/values-ci.yaml`).
7. Tests (`tests/repo/test_root_chart.py`): `test_platform_config_tls_and_dns` asserts `listeners["http"]["port"] == 8000` and `listeners["https"]["port"] == 8443`; `test_traefik_helmchartconfig` asserts the parsed `valuesContent` equals `{"deployment": {"replicas": 1}, "gateway": {"enabled": False}, "providers": {"kubernetesGateway": {"enabled": True}}, "ports": {"websecure": {"http": {"tls": {"enabled": True}}}}}`.
8. Spec INF-030 (the HelmChartConfig sentence) is amended to these keys.

### T10 — `tpl` in the `rootline.image` helper

`deploy/charts/rootline/values-gke.yaml` sets `image.registry: us-central1-docker.pkg.dev/{{ .Values.global.gcpProject }}/rootline`. Helm does not evaluate templates inside values files, and `global.gcpProject` arrives at sync time as an ArgoCD Helm parameter (INF-020). The helper therefore renders the registry with `tpl`: `{{ tpl .Values.image.registry (dict "Values" .Values) }}/{{ .component }}:{{ .Values.image.tag }}`. The registry string may reference only `.Values.*`. This is the chosen mechanism; the rejected alternative is a root-chart parameter `image.registry` computed in `deploy/root/templates/apps.yaml`, which needs a per-Application parameter list the root chart does not have and would make `deploy/charts/rootline` render a wrong registry when templated alone.

### T11 — One source for the `copy-ca` image

`copyCa.image` in `deploy/charts/platform-config/values.yaml` duplicates `versions.yaml` key `kubectl-image`. It is replaced by a generated file:

1. **W1-T11** (fix round, `scripts/render_versions.py`): new constant `PLATFORM_CONFIG_KEYS = ["kubectl-image"]` and a new output `deploy/charts/platform-config/files/versions.yaml` with content `"# GENERATED by scripts/render_versions.py from versions.yaml. Do not edit.\n" + yaml.safe_dump({k: data[k] for k in PLATFORM_CONFIG_KEYS}, sort_keys=True)`. `render()` includes this output only when `deploy/charts/platform-config/Chart.yaml` exists (it does not on `feat/w1-observability-postgres`, so `--check` passes there). The module docstring lists the output.
2. **W1-T10** (T1 step 3): deletes the `copyCa` key and its comment from `deploy/charts/platform-config/values.yaml`; `templates/ca-configmap.yaml` reads `{{- $kubectl := index (.Files.Get "files/versions.yaml" | fromYaml) "kubectl-image" }}` and renders `image: {{ printf "%s:v%s@%s" $kubectl.repo $kubectl.version $kubectl.digest }}` (on 2026-11-27 `docker.io/rancher/kubectl:v1.36.2@sha256:06c7a7a9772737494ae1e0c3af90f1b5385630c147e47c1c7cea92f4bed55fbe`); runs `uv run python scripts/render_versions.py` and commits the generated file. `test_copy_ca_image_matches_versions_yaml` becomes: the generated file parsed with `yaml.safe_load` equals `{"kubectl-image": <versions.yaml row>}`, and the image of container `copy-ca` in the rendered Job equals `<repo>:v<version>@<digest>` of that row.
3. The path is added to the schedule YAML `always_allowed` list and to the overview §7.4 "Generated files" row, so every PR merged after W1-P3 that changes `kubectl-image` in `versions.yaml` regenerates it with `uv run python scripts/render_versions.py`.

### O1 — Collector object names

The collector is DaemonSet `otel-collector-agent` (chart naming for `fullnameOverride: otel-collector` and `mode: daemonset`; its ConfigMap is also `otel-collector-agent`). The Service stays `otel-collector` (ports 4317, 4318), because WKL-010 step 5, PG-12 and the `rootline.otelEnv` helper use `otel-collector.observability.svc.cluster.local`. Spec ARC-001 (row "OTel Collector"), WKL-020 and SEC-090 `disallow-privileged`, and W3-T12 Step 3, name `otel-collector-agent`.

### O2 — Collector component names

The chart default `rewriteDeprecatedComponentNames: true` stays (no key is set), and the values file writes the new names directly, so the values file and the rendered config agree and nothing depends on deprecated aliases. WKL-020 lists exactly: receivers `otlp` and `file_log`; processors `memory_limiter`, `k8s_attributes`, `batch`; exporters `otlp_grpc/tempo`, `otlp_http/prometheus`, `otlp_http/loki`. Rejected: `rewriteDeprecatedComponentNames: false`, which keeps names that the collector reports as deprecated and that a future collector release removes.

### O3 — Container log collection under Pod Security (owner confirmation required)

PSS `baseline` forbids every `hostPath` volume, read-only or not, so no collector configuration that reads `/var/log/pods` is admitted in a `baseline` namespace. The options were:

| Option | Effect | Verdict |
|---|---|---|
| (a) Keep `file_log`; namespace `observability` PSS `enforce: privileged`; Kyverno restores the `baseline` checks for every other pod from W3-T12 | one namespace label; no DNS or spec-wide renames; Prometheus, Loki, Tempo, Alertmanager, the operator and kube-state-metrics lose PSS enforcement until W3-T12 | **chosen** |
| (b) Drop `file_log` from WKL-020 | spec scope change; loses stdout logs of every `shop` and `rootline` container that does not export logs over OTLP, which the agent uses as evidence | rejected (scope) |
| (c) Move the collector to its own `privileged` namespace | least privilege, but Service `otel-collector.observability.svc.cluster.local` is already used by WKL-010 step 5, PG-12, the W1-T09 render output and `rootline.otelEnv`, so every one of them would change | rejected (not simplest) |

Option (a), exactly:

1. **Namespace (W1-T10, `deploy/charts/namespaces`).** `observability` gets `pod-security.kubernetes.io/enforce: privileged`, `pod-security.kubernetes.io/enforce-version: latest`, plus `pod-security.kubernetes.io/warn: baseline`, `pod-security.kubernetes.io/warn-version: latest`, `pod-security.kubernetes.io/audit: baseline`, `pod-security.kubernetes.io/audit-version: latest`, so every `baseline` violation stays visible as an API warning and an audit annotation. In `values.yaml` the entry is `{name: observability, pss: privileged, warn: baseline, audit: baseline, defaultDeny: true}`; the template renders the `warn` and `audit` label pairs only for entries that set those keys. `test_namespaces_pss` expects `observability` = `privileged`, and a new assertion checks the four `warn`/`audit` labels on `observability` only.
2. **Collector values (W1-T11).** `presets.logsCollection.enabled: false` (so the chart adds no `/var/lib/docker/containers` volume; k3s and GKE run containerd, whose `/var/log/pods` files are regular files); an explicit `file_log` receiver with exactly the settings the preset would add (`include` from WKL-020, `start_at: end`, `include_file_path: true`, `include_file_name: false`, `retry_on_failure: {enabled: true}`, `operators: [{type: container, id: container-parser, max_log_size: 102400}]`); `extraVolumes: [{name: varlogpods, hostPath: {path: /var/log/pods, type: Directory}}]`; `extraVolumeMounts: [{name: varlogpods, mountPath: /var/log/pods, readOnly: true}]`; container `securityContext: {runAsUser: 0, runAsGroup: 0, runAsNonRoot: false, allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: [ALL]}, seccompProfile: {type: RuntimeDefault}}`. UID 0 is needed because the kubelet writes the log files as `root:root` mode `0640` (unverified on k3s `v1.36.6+k3s1` on 2026-11-27; W1-T12 Step 5 verifies it). The unused chart-default components are removed with `null`: `config.receivers.jaeger`, `config.receivers.zipkin`, `config.receivers.prometheus`, `config.exporters.debug`. The full block is in W1-T11 Step 2.
3. **Failure rule (W1-T12 Step 5).** After `task up`, `kubectl -n observability logs ds/otel-collector-agent | grep -ci "permission denied"` must print `0`. If it prints more, the W1-T12 implementer adds `DAC_READ_SEARCH` to `capabilities.add` of the collector container, re-syncs, repeats the check, and records the result in `wiki/components/otel-collector.md`. If the count is still not `0`, W1-T12 reports `STATUS: BLOCKED`.
4. **Compensating control (W3-T12, SEC-090 `disallow-privileged`).** The policy gains two rules for namespace `observability`: rule `observability-baseline` validates every Pod with `podSecurity: {level: baseline, version: latest, exclude: [{controlName: "HostPath Volumes"}]}`; rule `observability-hostpath` denies a Pod with any `hostPath` volume unless the Pod has labels `app.kubernetes.io/name: opentelemetry-collector` and `component: agent-collector`, its only `hostPath` volume has `path: /var/log/pods`, and every mount of that volume has `readOnly: true`. Kyverno auto-generates the same rules for DaemonSet `otel-collector-agent`. Both rules are `Enforce` in every environment. `kyverno test` cases: one pass (the collector pod) and one fail (a Prometheus-labelled pod with a `hostPath`) for `observability-hostpath`; one fail (a pod with `hostNetwork: true`) for `observability-baseline`.
5. **Accepted window.** From the W1-P3 merge until W3-T12 is merged, `observability` has no `baseline` enforcement. Only the local k3d cluster exists in that window (the first GKE cluster is created in week 7, W7-T05).

#### Owner confirmation

O3 lowers the PSS enforce level of `observability` from `baseline` (ARC-010, approved by the owner) to `privileged`. The implementers proceed with option (a), and the coordinator MUST ask the owner to confirm it (**[CONFIRM]**, W1 plan "W1-P3 integration steps" step 5) before the W1-P3 integration PR is merged into `develop`. If the owner chooses (b) or (c) instead, the planner re-plans W1-T10 and W1-T11 before that merge.

### O4 — NetworkPolicies of `observability` and `rootline-data`

These rules extend the default-deny policies of ARC-010 (rendered by W1-T10 Step 4) and the flows of ARC-001, ARC-020 and WKL-020. Namespaces are matched by label `kubernetes.io/metadata.name`. All ports are TCP. Final text: W1-T11 Step 2 and Step 3.

`observability` (`deploy/charts/observability/templates/networkpolicies.yaml`):

| Policy | Pod selector | Direction | Peer | Ports | Reason |
|---|---|---|---|---|---|
| `allow-same-namespace` | all pods | ingress | all pods of `observability` | all | collector → Tempo 4317, Loki 3100, Prometheus 9090; Prometheus scrapes; Tempo → Prometheus remote write |
| `allow-otlp-ingress` | `app.kubernetes.io/name: opentelemetry-collector`, `component: agent-collector` | ingress | all namespaces (`namespaceSelector: {}`) | 4317, 4318 | OTLP from `shop` and `rootline` to the collector only; Tempo's 4317 is no longer open to other namespaces |
| `allow-query-ingress` | all pods | ingress | namespaces `rootline`, `observability` | 9090, 3100, 3200 | `mcp-telemetry` live queries (ARC-001) |
| `allow-alertmanager-ingress` | all pods | ingress | namespace `observability` | 9093 | Prometheus → Alertmanager |
| `allow-operator-webhook-ingress` | `app.kubernetes.io/name: kube-prometheus-stack-prometheus-operator` | ingress | `ipBlock: {cidr: 0.0.0.0/0}` | 10250 | the kube-apiserver calls the operator's admission webhook from a node or control-plane address, which no pod or namespace selector matches; only the operator pods are opened |
| `allow-egress-pods` | all pods | egress | all namespaces (`namespaceSelector: {}`) | all | scraping pod targets in every namespace; collector → Tempo/Loki/Prometheus; Alertmanager → `api` webhook |
| `allow-egress-apiserver` | all pods | egress | `ipBlock: {cidr: 0.0.0.0/0}` | 443, 6443 | kube-apiserver for the operator, kube-state-metrics, the collector's `k8s_attributes`, Prometheus service discovery and the admission patch Jobs; 6443 is the k3s API server endpoint port, 443 the GKE one |
| `allow-egress-kubelet` | `app.kubernetes.io/name: prometheus` (set by the Prometheus Operator on Prometheus pods) | egress | `ipBlock: {cidr: 0.0.0.0/0}` | 10250 | Prometheus scrapes the kubelet and cAdvisor on the node address (ServiceMonitor `kubelet`) |

The former single policy `allow-egress-scrape` is split into the last three rows, so only Prometheus may open 10250. W1-T11 verifies the Prometheus pod label in W1-T12 Step 5 (`kubectl -n observability get pods -l app.kubernetes.io/name=prometheus` lists the Prometheus pod).

`rootline-data` (`deploy/charts/postgres/templates/networkpolicies.yaml`): `allow-postgres-clients` (ingress 5432 from namespaces `rootline`, `keycloak`), `allow-cnpg-operator` (ingress 8000 and 5432 from namespace `cnpg-system`), `allow-same-namespace` (ingress and egress among `rootline-data` pods) and `allow-egress-apiserver` (egress to `ipBlock: {cidr: 0.0.0.0/0}` on 443 and 6443, for the CNPG instance manager and initdb Job). These extend DB-001 and the plan's W1-T11 Step 3 rule, which named only the ingress rules.

### O5 — Unreachable control-plane targets of kube-prometheus-stack

`kube-prometheus-stack` values set `kubeControllerManager: {enabled: false}`, `kubeEtcd: {enabled: false}`, `kubeScheduler: {enabled: false}`, `kubeProxy: {enabled: false}`. On k3s these components run inside the k3s server process with metrics on `127.0.0.1` only, and on GKE they belong to the managed control plane (and GKE Dataplane V2 has no kube-proxy), so their Services in `kube-system` and their ServiceMonitors would only produce targets that are always down. ServiceMonitors `kubelet`, `apiserver`, `coredns`, `kube-state-metrics`, `operator`, `prometheus` and `alertmanager` stay. Test: no rendered Service or ServiceMonitor name contains `kube-controller-manager`, `kube-etcd`, `kube-scheduler` or `kube-proxy`.

## Consequences

- `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`: "Execution schedule" row W1-P3 (task order) and the new "W1-P3 integration steps"; "Task W1-T10" amendment note, root values block (`prometheus-crds`), Step 1 tests, Steps 2, 3, 4, 5 (`gateway.yaml`, `ca-configmap.yaml`, `generators.yaml`), 6 (T10) and 8 (T8); "Task W1-T11" amendment note, "Files", Step 1 tests, Step 2 values block and paragraphs (O1 to O5, T1, T11), Step 3 network policies; "Task W1-T12" "Files", Step 3 item 1 and Step 5 (T6, O3 item 3, O4).
- `docs/superpowers/plans/2026-11-26-rootline-w3-identity-mcp.md` "Task W3-T12": amendment note, "Files", Step 3 (O1, O3 item 4, T7). `docs/superpowers/plans/2026-11-26-rootline-w7-cloud-benchmark.md` "Task W7-T02": amendment note, "Files", Steps 2 and 3 (T5, T9). `docs/superpowers/plans/2026-11-26-rootline-w6-console-e2e.md` "Task W6-T09": amendment note and Step 2 (T9).
- `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`: W1-P3 task order W1-T09, W1-T11, W1-T10, W1-T14; `always_allowed` gains `deploy/charts/platform-config/files/versions.yaml`; W3-T12 `owns` gains `deploy/charts/postgres/templates/cluster.yaml`; W7-T02 `owns` gains the three paths of T5 item 3. `uv run python scripts/swarm_schedule.py validate` prints `schedule OK: 8 weeks, 39 stages, 94 tasks`.
- Spec `docs/superpowers/specs/2026-11-25-rootline-design.md`: ARC-001 row "OTel Collector", ARC-010 row `observability`, WKL-020, SEC-011 "Trust", SEC-090 row `disallow-privileged`, INF-030 HelmChartConfig sentence; §26 gains row PG-27.
- Overview `docs/superpowers/plans/2026-11-26-rootline-00-overview.md`: §5 gains PG-27 (the next free ADR number is 0047), §6 gains the PG-27 traceability row, §7.4 "Generated files" gains `deploy/charts/platform-config/files/versions.yaml`.
- `wiki/index.md` lists this ADR.
- W1-T10 and W1-T11 each get one fix round on their branches for the items assigned to them, plus the W1-T10 post-rebase step of T1. Neither task needs a new `owns` path: every file they change is in their current `owns` or is an always-allowed generated file.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| T1: keep the `repo`/`chartVersion` overrides permanently | two sources for one version; GEN-050 requires `versions.yaml` to be the only one |
| T1: keep the schedule order and let W1-T10 drop the overrides in a separate PR | that PR would be a W1-S3 task editing W1-T10's files; reordering two tasks of one parallel stage costs nothing |
| T8: keep `--allow-missing` after W1-P3 | after W1-P3 every enabled local chart exists; a flag that hides a missing chart only hides defects |
| T9: listeners on 80/443 with Traefik entry points moved to 80/443 | binding ports below 1024 needs `NET_BIND_SERVICE` or root in the Traefik pod, and k3s, kind and GKE values would all diverge from chart defaults |
| T9: keep the chart-default `traefik-gateway` | an unused object on the same entry point; no route attaches to it |
| T11: pass the image as a root-chart Helm parameter | `render_manifests.py` and the tests template `platform-config` alone and would still need a default copy |
| O3 (b), (c) | see the O3 table |
| O2: `rewriteDeprecatedComponentNames: false` | see O2 |

## Spec references

INF-020, INF-021, INF-030, INF-031, INF-041, ARC-001, ARC-010, ARC-030, WKL-010 (step 5), WKL-020, SEC-011, SEC-090, SEC-100, GEN-050, DB-001, DB-002; spec §0.3, §26; plan overview §5, §6, §7.4, §7.6; PG-10, PG-12, PG-22.
