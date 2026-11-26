# Cluster smoke checks

This directory lists, per deployed component, the checks that `scripts/cluster_smoke.py` (gate check G12 of overview `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §7.7) runs against the running local cluster after an integration PR merged. Requirements: PG-16, ARC-020, ARC-030.

G12 runs in the `deferred_to` stage on the new `develop`, never inside a parallel worktree: `task images`, then `task up REVISION=develop`, then `uv run python scripts/cluster_smoke.py` (defaults: `--context k3d-rootline`, `--timeout 1200`).

## File format

One YAML file per component. Validation schema: [`schema.json`](schema.json) (JSON Schema draft 2020-12).

| Key | Type | Required | Constraint |
|---|---|---|---|
| `component` | string | yes | `^[a-z][a-z0-9-]*$`, for example `api` or `mcp-k8s` |
| `checks` | list | yes | at least 1 item; each item is one of the three kinds below |

Every check has `name` (`^[a-z][a-z0-9-]*$`, unique within the file) and `kind`.

| `kind` | Other keys (all required) | What `cluster_smoke.py` runs | Passes when |
|---|---|---|---|
| `http` | `namespace` (string), `service` (string), `port` (integer 1 to 65535, the Service port), `path` (string starting with `/`), `expect_status` (integer 100 to 599) | `kubectl --context <ctx> -n <namespace> port-forward svc/<service> <local>:<port>` with `<local>` a free local port, then `GET http://127.0.0.1:<local><path>`; redirects are never followed, so `expect_status` may be a 3xx code | the response status equals `expect_status` |
| `exec` | `namespace` (string), `pod_selector` (label selector string, for example `app.kubernetes.io/name=api`), `container` (string), `command` (list of at least 1 string), `expect_exit` (integer 0 to 255) | `kubectl --context <ctx> -n <namespace> get pods -l <pod_selector> -o jsonpath={.items[0].metadata.name}`, then `kubectl --context <ctx> -n <namespace> exec <pod> -c <container> -- <command...>` | the exit code equals `expect_exit` |
| `argocd_app` | `app` (ArgoCD Application name in namespace `argocd`), `expect` (the literal `Synced/Healthy`) | `kubectl --context <ctx> -n argocd get application <app> -o jsonpath={.status.sync.status}/{.status.health.status}` | the output equals `expect` |

Overview §7.7 lists the `exec` keys as `{pod_selector, container, command, expect_exit}` without a namespace. W1-T16 makes `namespace` a required key of `exec` because `kubectl get pods` and `kubectl exec` need it.

Example, file `tests/smoke/api.yaml`:

```yaml
component: api
checks:
  - name: readyz
    kind: http
    namespace: rootline
    service: api
    port: 80
    path: /readyz
    expect_status: 200
  - name: python-runs
    kind: exec
    namespace: rootline
    pod_selector: app.kubernetes.io/name=api
    container: api
    command: [python, -c, "print(1)"]
    expect_exit: 0
  - name: workload-synced
    kind: argocd_app
    app: workload
    expect: Synced/Healthy
```

## File name

The file name is `<component>.yaml`, equal to the `component` value. One file per component; no other task edits it (overview §7.4).

## Who creates a file

The task that deploys the component creates its smoke file in the same commit series. The schedule lists the file under that task's `owns`.

## What `cluster_smoke.py` does, in order

| Step | Behaviour | Failure behaviour |
|---|---|---|
| 1. ArgoCD | polls `kubectl --context <ctx> -n argocd get applications.argoproj.io -o json` every 15 s until at least 1 Application exists and every Application is `Synced` and `Healthy` | after `--timeout` seconds prints `FAIL argocd/apps: not Synced/Healthy after <n> s: <names>` |
| 2. Memory | calls `memory_requests_gib` of `scripts/doctor.py` (W1-T06) on `kubectl get pods -A -o json`; limit 9.5 GiB (S2) | above the limit prints `FAIL cluster/memory-requests`; when `scripts/doctor.py` does not exist prints `SKIP cluster/memory-requests: scripts/doctor.py missing` |
| 3. Checks | loads `tests/smoke/*.yaml` in file-name order, validates each file, runs each check in file order | an invalid file (schema violation, wrong file name or a check `name` used twice in the file) prints `FAIL smoke/<file>: <violation>` and the remaining files are not run; a check that does not pass prints `FAIL <component>/<name>: <detail>`; a port-forward that is not ready after 30 s or a request error is a `FAIL` of that check |

Output is one line per check, `PASS|FAIL|SKIP <component>/<name>: <detail>`. Exit code 0 when no line starts with `FAIL`, otherwise 1.

## Exemption lines

Smoke checks have no exemption line. The exemption lines `registry-removal:`, `test-removal:` and `baseline-change:` belong to checks G8, G9 and G10 and are documented in [`../registry/README.md`](../registry/README.md).
