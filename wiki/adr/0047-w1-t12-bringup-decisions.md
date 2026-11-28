# 0047 — Bring-up decisions from W1-T12: Application namespaces, sync retry, root diff and node DNS (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-28 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

This ADR holds four decisions, D1, D2, D3 and E1. They answer the three root-chart defects and the one environment problem that W1-T12 (`task up`, branch `feat/w1-task-up`, PR #30, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T12") found when it first brought up the local k3d cluster on 2026-11-27. The symptoms are recorded in `wiki/components/argocd.md` section "Defects found by W1-T12" on `feat/w1-task-up` at `7281427`. Defect D4 in that section (Application `workload` has no `workload/` path because W1-T09 steps 6 and 7 have not run) is not a spec gap: it closes when W1-T09 steps 6 and 7 run in W1-S3, and this ADR does not change it.

## Context

| ID | Symptom | Cause | Gap in the documents |
|---|---|---|---|
| D1 | Application `observability` deploys Prometheus, Loki, Tempo and the collector into namespace `argocd`, where Pod Security rejects the collector DaemonSet | entry `observability` of `deploy/root/values.yaml` has no `namespace` key; `deploy/root/templates/apps.yaml` falls back to `argocd` for every non-`env-repo` Application; the subcharts place their objects in `.Release.Namespace` | the W1 plan root values block ("Task W1-T10", "Interfaces") omits the key and its template has the fallback; no rule says that the destination namespace must be explicit |
| D2 | Application `platform-config` stays `OutOfSync`; ExternalSecrets `pg-*` never exist; `rootline-pg-1-initdb` fails with `secret "pg-rootline-migrator" not found` | the first sync (wave -2) ran while the External Secrets validating webhook had no endpoints (`failed calling webhook "validate.clustersecretstore.external-secrets.io"`); `syncPolicy.automated` without `retry` does not retry a failed sync of the same revision | INF-021 and the W1-T10 template define no `syncPolicy.retry` |
| D3 | Application `root` stays `OutOfSync`, listing only `Application/kyverno` | ArgoCD `v3.6.3` adds the finalizers `pre-delete-finalizer.argocd.argoproj.io` and `pre-delete-finalizer.argocd.argoproj.io/cleanup` to Application `kyverno` (the kyverno chart has a PreDelete hook); the rendered list is `[resources-finalizer.argocd.argoproj.io]`, and the diff does not ignore finalizers | no document defines `ignoreDifferences` for Application `root`; `scripts/wait_apps.py` waits for `root` (W1-T12 Step 3 item 7 after PG-28; item 6 before), so `task up` can never succeed |
| E1 | every Application stays `Unknown` with `failed to list refs: dial tcp 79.72.77.199:22: connect: connection timed out` | WSL writes `search codegen.net` into `/etc/resolv.conf`; Docker copies the search list into the k3d node container; the kubelet copies the node search list into every pod (`ndots:5`); the workstation's DNS server answers every name below `codegen.net` with `79.72.77.199`, so the ArgoCD repo-server resolves `github.com` as `github.com.codegen.net` | INF-030 and W1-T12 do not say how pods resolve external names when the host has a search domain |

## Verification performed on 2026-11-27

All commands ran in WSL Ubuntu 26.04 against k3d cluster `rootline` (k3d `v5.9.0`, k3s `v1.36.6+k3s1`, ArgoCD chart `10.20.0`, image `quay.io/argoproj/argocd:v3.6.3`), created by `task up` on `feat/w1-task-up` and synced from the scratch branch `fix/w1-t12-verify-scratch` (commit `17f2bd6`, not merged).

| Fact | How it was verified |
|---|---|
| With `namespace: observability` on entry `observability`, the pods run in namespace `observability` and the W1-T12 Step 5 label checks pass | W1-T12 report; `kubectl -n argocd get applications` shows destination namespace `observability` for Application `observability` |
| With `retry: {limit: 5, backoff: {duration: 10s, factor: 2, maxDuration: 3m}}` on `platform-config`, `platform-config` and `postgres` are `Synced`/`Healthy` | `kubectl -n argocd get application platform-config -o jsonpath='{.spec.syncPolicy}'` prints that `retry` object; both Applications `Synced`/`Healthy` |
| Live Application `kyverno` has `metadata.finalizers` `["resources-finalizer.argocd.argoproj.io","pre-delete-finalizer.argocd.argoproj.io","pre-delete-finalizer.argocd.argoproj.io/cleanup"]` | `kubectl -n argocd get application kyverno -o jsonpath='{.metadata.finalizers}'` |
| With `spec.ignoreDifferences: [{group: argoproj.io, kind: Application, jsonPointers: [/metadata/finalizers]}]` on Application `root` (live patch), `root` is `Synced`/`Healthy` | `kubectl -n argocd get application root -o jsonpath='{.spec.ignoreDifferences}'`; `kubectl -n argocd get applications` |
| WSL `/etc/resolv.conf` is `nameserver 10.255.255.254` and `search codegen.net`; `getent hosts github.com.codegen.net` answers `79.72.77.199` | `cat /etc/resolv.conf`; `getent hosts github.com.codegen.net` in WSL |
| Node container `k3d-rootline-server-0`, after the workaround, has `/etc/resolv.conf` with header `# Generated by Docker Engine.` / `# This file can be edited; Docker Engine will not make further changes once it has been modified.`, `nameserver 172.23.0.1`, `options ndots:0`, and no `search` line; Docker network `k3d-rootline` has subnet `172.23.0.0/16`, gateway `172.23.0.1` | `docker exec k3d-rootline-server-0 cat /etc/resolv.conf`; `docker network inspect k3d-rootline --format '{{json .IPAM.Config}}'` |
| ArgoCD repo-server pods created after the workaround have exactly `search argocd.svc.cluster.local svc.cluster.local cluster.local`, `nameserver 10.43.0.10`, `options ndots:5`, and resolve `github.com` to a GitHub address (`57.155.223.240`), not `79.72.77.199` | `kubectl -n argocd exec deploy/argocd-repo-server -- cat /etc/resolv.conf`; `kubectl -n argocd exec deploy/argocd-repo-server -- getent hosts github.com` |
| The k3s CoreDNS Corefile forwards with `forward . /etc/resolv.conf`; CoreDNS pods have `dnsPolicy: Default`, so their `/etc/resolv.conf` comes from the kubelet's `resolv-conf` file | `kubectl -n kube-system get cm coredns -o jsonpath='{.data.Corefile}'` |
| `kubectl -n argocd patch application <name> --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{}}}'` starts a sync operation (`status.operationState.phase: Running`, `initiatedBy.username: admin`) | run against Application `gateway-api-crds`; that run then ended in `Error` because the workstation's connection to `github.com` timed out at that moment (a host `curl` to the same URL also timed out after 20 s), not because of the command |
| `kubectl rollout restart deployment -n <ns>` restarts every Deployment of the namespace | `kubectl rollout restart --help` (kubectl `v1.37.3`), first example |

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). No decision changes cost, security level or scope: D1 to D3 change ArgoCD object fields, and E1 changes the DNS search list inside the local k3d node only.

### D1 — Every Application names its destination namespace

Rule (spec INF-020, PG-28): every entry of `apps` in `deploy/root/values.yaml` MUST have a `namespace` key (string), which becomes `spec.destination.namespace` of the rendered Application. `deploy/root/templates/apps.yaml` has no default; the destination line is exactly:

```yaml
    namespace: {{ required (printf "deploy/root/values.yaml apps.%s has no namespace" $name) $app.namespace }}
```

A missing key makes `helm template deploy/root` fail with `deploy/root/values.yaml apps.<name> has no namespace`.

| Entry | `namespace` | Reason |
|---|---|---|
| `namespaces` | `argocd` | only cluster-scoped Namespaces and NetworkPolicies that set `metadata.namespace`; `argocd` is the value it had through the fallback |
| `gateway-api-crds` | `argocd` | only cluster-scoped CRDs; value it had through the fallback |
| `cert-manager` | `cert-manager` | unchanged |
| `external-secrets` | `external-secrets` | unchanged |
| `cnpg-operator` | `cnpg-system` | unchanged |
| `kyverno` | `kyverno` | unchanged |
| `chaos-mesh` | `chaos-mesh` | unchanged |
| `prometheus-crds` | `observability` | unchanged |
| `traefik` | `traefik` | unchanged |
| `platform-config` | `argocd` | every namespaced object sets `metadata.namespace`; value it had through the fallback |
| `postgres` | `rootline-data` | every object is in `rootline-data` |
| `observability` | `observability` | the defect fix; the subcharts use `.Release.Namespace` |
| `keycloak` | `keycloak` | ARC-001 namespace of Keycloak |
| `argocd-accounts` | `argocd` | the Job and its ServiceAccount run in `argocd` (W2-T08 Step 2) |
| `rootline` | `rootline` | ARC-001 namespace of the Rootline services |
| `workload` | `shop` | unchanged (it had `shop` through the `env-repo` fallback) |
| `demo-seed` | `rootline` | ARC-001 row `demo-seed` |

Decision rule for an entry added after 2026-11-27 (by W2 to W8 tasks): `namespace` is the namespace that receives the chart's namespaced objects that do not set `metadata.namespace` (the chart's `.Release.Namespace`). When every namespaced object of the chart sets `metadata.namespace`, or the chart has only cluster-scoped objects, the value is `argocd`.

Recovery on a cluster that synced `observability` into `argocd` before the fix: a sync that waits for DaemonSet `otel-collector-agent` in `argocd` stays `Running` and blocks the new revision; end it with `kubectl -n argocd patch application observability --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'`. The next automated sync deploys into `observability`, and `prune: true` deletes the objects left in `argocd`.

### D2 — Sync retry on every Application

Every Application rendered by `deploy/root/templates/apps.yaml` (all kinds, `workload` included) and Application `root` (D3) carry exactly:

```yaml
  syncPolicy:
    retry:
      limit: 10
      backoff: {duration: 10s, factor: 2, maxDuration: 3m}
```

In `apps.yaml` the block is literal text after `syncOptions` (no values key). In `scripts/up.py` the same object is the module constant `SYNC_RETRY = {"limit": 10, "backoff": {"duration": "10s", "factor": 2, "maxDuration": "3m"}}`, and `tests/repo/test_root_chart.py` compares every rendered Application's `spec.syncPolicy.retry` with `scripts.up.SYNC_RETRY`, so the two places cannot differ.

Reason for the numbers: the delays are 10, 20, 40, 80, 160, 180, 180, 180, 180 and 180 s (1210 s in total), which is longer than the 1200 s that `scripts/wait_apps.py` waits (W1-T12 Step 3 item 7). A transient failure (a webhook without endpoints, an image pull, the workstation's slow connection to GitHub) is therefore retried for as long as `task up` waits. The verified value `limit: 5` (310 s of delays) is shorter than that wait; `limit: -1` (unlimited) would keep retrying a permanent error after `task up` has already reported it.

`workload` gets the retry too: a retry repeats a failed sync operation of the target revision and does not revert live drift, so GEN-012 (`selfHeal: false`) still holds.

Failure behaviour: after the tenth failed retry the Application keeps `status.operationState.phase: Failed` and ArgoCD does not start another automated sync of the same revision. Recovery after the cause is fixed: `kubectl --context k3d-rootline -n argocd patch application <name> --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{}}}'` (starts one manual sync), or push a new commit to the tracked revision.

### D3 — Application `root` ignores child-Application finalizers

`scripts/up.py` `root_application()` sets, on Application `root`:

```yaml
spec:
  ignoreDifferences:
    - group: argoproj.io
      kind: Application
      jsonPointers: [/metadata/finalizers]
  syncPolicy:
    automated: {prune: true, selfHeal: true}
    syncOptions: [RespectIgnoreDifferences=true]
    retry:
      limit: 10
      backoff: {duration: 10s, factor: 2, maxDuration: 3m}
```

The field is set in `root_application()`, not in the root chart, because Application `root` is not a template of `deploy/root`: the chart renders the child Applications, and the diff that stays `OutOfSync` is computed by `root` over those children. A child cannot ignore a difference of its own `metadata`. The other two creators of Application `root` set the same three fields: `scripts/e2e.py up` (W6, `env=ci`) and `kubectl_manifest.root_app` in `infra/terraform/cluster/argocd.tf` (W7, `env=gke`); spec INF-021 states them.

`RespectIgnoreDifferences=true` keeps the live value of an ignored field when `root` syncs. Without it, every sync of `root` (each new commit on the tracked revision) would write the rendered list `[resources-finalizer.argocd.argoproj.io]` back onto the child and remove the two PreDelete finalizers that ArgoCD added; this behaviour was not observed on the cluster and is the reason, not a verified fact. With it, an existing child keeps whatever finalizers it has, and a new child is created with `[resources-finalizer.argocd.argoproj.io]`.

`scripts/wait_apps.py` depends on D3: `step_root()` returns `["root", *children]`, so `wait_apps` waits for `root` to be `Synced`/`Healthy`; without D3 it times out after 1200 s and `task up` exits 1.

### E1 — `task up` removes the search list from the k3d node

Repository fix in `scripts/up.py`, run on every `task up` (new Step 3 item 2 in W1-T12, directly after the cluster step and before images and ArgoCD):

1. `docker exec k3d-rootline-server-0 cat /etc/resolv.conf` (timeout 60 s).
2. `strip_search_lines(text)` removes every line whose first whitespace-separated token is `search` or `domain` and keeps every other line, its order and its line ending.
3. When the result equals the input, print `node DNS: k3d-rootline-server-0 has no search or domain line` and stop.
4. Otherwise write it with `docker exec -i k3d-rootline-server-0 sh -c 'cat > /etc/resolv.conf'` (stdin = the stripped text; `cat >` writes through Docker's bind mount, a rename would fail), re-read the file as in 1 and fail when `strip_search_lines` of the re-read text differs from it; print `node DNS: removed search and domain lines from k3d-rootline-server-0:/etc/resolv.conf`.
5. When the file changed and `kubectl --context k3d-rootline get namespace argocd -o name` exits 0 (a cluster that existed before this run), run `kubectl --context k3d-rootline -n argocd rollout restart deployment` and `kubectl --context k3d-rootline -n argocd rollout restart statefulset`, and print `node DNS: restarted deployments and statefulsets in namespace argocd`. On a new cluster the namespace does not exist yet, and the ArgoCD pods created in the Helm step (W1-T12 Step 3 item 4) get the clean list.

Pods in `kube-system` that k3s starts during `k3d cluster create` (CoreDNS, Traefik, metrics-server, local-path-provisioner, `svclb-traefik`) keep the old search list and are not restarted: CoreDNS forwards with `forward . /etc/resolv.conf`, which does not apply a search list, and the others do not resolve names outside the cluster.

Persistence: Docker does not change a container's `resolv.conf` once it has been edited (header of the file, verified above), so the edit survives `task stop` and `task start`. `task down` deletes the node container; the next `task up` creates a new one and repeats the step. On a host without a `search` or `domain` line the step changes nothing. The nameserver line (the Docker network gateway, `172.23.0.1` on 2026-11-27) stays as Docker and k3d wrote it.

The proof check (W1-T12 Step 5):

```bash
docker exec k3d-rootline-server-0 grep -cE '^(search|domain)[[:space:]]' /etc/resolv.conf
kubectl --context k3d-rootline -n argocd exec deploy/argocd-repo-server -c repo-server -- grep '^search' /etc/resolv.conf
kubectl --context k3d-rootline -n argocd exec deploy/argocd-repo-server -c repo-server -- getent hosts github.com
```

Expected: the first prints `0` (grep exits 1 when the count is 0; that exit code is expected); the second prints exactly `search argocd.svc.cluster.local svc.cluster.local cluster.local`; the third prints one line whose address is not `79.72.77.199` and whose name is `github.com`. When the workstation itself cannot reach `github.com`, Applications show `TLS handshake timeout` or `context deadline exceeded`, not `79.72.77.199`; that is a network problem outside E1.

No owner step is required. The workstation-specific cause (the Windows DNS suffix that WSL copies into `/etc/resolv.conf`) is left unchanged; `wiki/runbooks/local-up.md` "Troubleshooting" records the symptom, the cause and the step that fixes it.

The same helper is used by `scripts/e2e.py up` (W6) for kind node container `rootline-e2e-control-plane` with context `kind-rootline-e2e`, right after `kind create cluster` and before ArgoCD is installed (unverified for kind on 2026-11-27; W6-T09 Step 3 verifies it with the same three commands, namespace `argocd`, context `kind-rootline-e2e`).

Interface (`scripts/up.py`):

| Name | Signature | Behaviour | Errors |
|---|---|---|---|
| `NODE` | `str = "k3d-rootline-server-0"` | the only kubelet node of INF-030 (`servers: 1`, `agents: 0`) | none |
| `strip_search_lines` | `(text: str) -> str` | pure; removes lines whose first token is `search` or `domain`; keeps comments, blank lines, other lines and line endings | none |
| `fix_node_dns` | `(node: str = NODE, context: str = CONTEXT) -> bool` | steps 1 to 5 above; returns `True` when the file changed | `StepError` with `<command> exited <code>: <stderr>` when a `docker` command or a `rollout restart` exits non-zero or times out (60 s each); `StepError("node DNS: search or domain line still present in <node>:/etc/resolv.conf")` when the re-read check fails; `kubectl get namespace` exiting non-zero means "namespace absent", not an error |

## Consequences

- W1-T12 (fix round on `feat/w1-task-up`) applies all four decisions: it edits `deploy/root/values.yaml`, `deploy/root/templates/apps.yaml`, `tests/repo/test_root_chart.py`, `scripts/up.py`, `tests/repo/test_up_helpers.py`, `wiki/components/argocd.md` and `wiki/runbooks/local-up.md`, then reruns W1-T12 Steps 4, 5 and 8. W1-S3 is a sequential stage, so no `owns` list applies (overview §7.4).
- The W1 plan root values block and `apps.yaml` template ("Task W1-T10", "Interfaces" and Step 3) carry the `namespace` keys, the `required` destination line and the `retry` block.
- Spec INF-020 (namespace rule), INF-021 (retry on every Application; the three fields of Application `root`), INF-030 (node DNS step), the `task up` row of GEN-060 and the `kubectl_manifest.root_app` row of §16.3 are amended.
- W6-T09 Step 3 (`scripts/e2e.py up`) and W7-T02 Step 1 (`argocd.tf`) set the D3 fields on their Application `root`; W6-T09 also calls `fix_node_dns`.
- `wait_apps` reports `root` `Synced`/`Healthy` once D3 is applied.

## Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| D1 | keep the fallback and add only `namespace: observability` | the next local chart without the key repeats the defect silently; `required` turns it into a render error that `tests/repo/test_root_chart.py` and CI catch |
| D1 | fallback to the Application name | `namespaces`, `gateway-api-crds`, `platform-config` and `argocd-accounts` have no namespace of that name |
| D2 | `limit: 5` (the verified value) | 310 s of retries is shorter than the 1200 s `task up` waits |
| D2 | `limit: -1` | retries a permanent error for good after `task up` has reported it |
| D2 | a values key per Application | no Application needs a different policy; one literal block is simpler |
| D3 | global `resource.customizations.ignoreDifferences.argoproj.io_Application` in `argocd-cm` via `deploy/upstream/argo-cd/values-{local,ci,gke}.yaml` | changes three values files and the ArgoCD Helm release for a difference that only `root` sees |
| D3 | render the two PreDelete finalizers in `apps.yaml` for `kyverno` | depends on which upstream chart has a PreDelete hook and on ArgoCD internals; breaks again when a chart adds or drops such a hook |
| D3 | `ignoreDifferences` in the root chart | the chart does not render Application `root`, and a child cannot ignore its own `metadata` difference for its parent |
| E1 | `--kubelet-arg=resolv-conf=` (empty) in `infra/k3d/rootline.yaml` | an empty `resolvConf` disables host DNS for pods with `dnsPolicy: Default` (KubeletConfiguration `resolvConf`); CoreDNS then has no upstream for `forward . /etc/resolv.conf` and no external name resolves, `github.com` included |
| E1 | `--kubelet-arg=resolv-conf=/etc/rootline/resolv.conf` with a file from the repository mounted into the node | the file needs a literal nameserver; the working one is the Docker network gateway (`172.23.0.1`), which Docker assigns when the network is created; pinning it needs a pinned subnet (collision with other Docker networks on the workstation) or a public resolver (bypasses the workstation's DNS and can be blocked) |
| E1 | owner step: `/etc/wsl.conf` `[network] generateResolvConf = false` with a hand-written `/etc/resolv.conf`, or Docker `daemon.json` `"dns-search": ["."]` | changes DNS for every program or container on the workstation and must be repeated on every new workstation; the repository fix covers all hosts and is a no-op where no search line exists |

## Spec references

INF-020, INF-021, INF-030, GEN-012, GEN-060 (`task up`), ARC-001, ARC-010, §16.3 (`kubectl_manifest.root_app`), §26 PG-28; plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T10" (Interfaces, Step 3) and "Task W1-T12" (amendment note, "Files", "Interfaces", Steps 1, 2b, 3, 5, 7); `docs/superpowers/plans/2026-11-26-rootline-w6-console-e2e.md` W6-T09 Step 3; `docs/superpowers/plans/2026-11-26-rootline-w7-cloud-benchmark.md` W7-T02 Step 1.
