# Local up

## GitOps repositories

This section is kept unchanged by tasks W1-T09 and W1-T12.

| Item | Value | Source |
|---|---|---|
| Repository URL | https://github.com/arkhash0309/rootline-env. Created by the owner after confirmation (overview §2 O-1, docs/superpowers/plans/2026-11-26-rootline-00-overview.md). | GEN-010 |
| Visibility | private | GEN-010 |
| Owner | arkhash0309 | GEN-010 |
| Local clone path | `/home/arkhash0309/projects/rootline-env` (WSL filesystem, never `/mnt/c`) | CLAUDE.md "Development environment" |
| Key in `/home/arkhash0309/projects/rootline/.env.local` (git-ignored) | `ROOTLINE_ENV_DIR=/home/arkhash0309/projects/rootline-env` | CLAUDE.md "Development environment" |
| Initial commit | on `main`, initial README commit `35d4916`, authored under the owner git identity, contains `README.md` only | GEN-010 |
| Branches | `main` is the only branch in this repository; ruleset `protect-main` is created in week 3 | GEN-024, SEC-081 |
| ArgoCD Application `workload` | tracks `main`, path `workload/` | GEN-012 |

Commit authorship by phase:

| Phase | Who commits | Identity | Requirement |
|---|---|---|---|
| Until ruleset `protect-main` exists (week 3) | the owner, from the local clone, for the README (`35d4916`), the workload render and tag `baseline-v1` (W1-T09 Step 7) | owner git identity | GEN-010, SEC-081 |
| From ruleset `protect-main` (week 3) | GitHub App `rootline-agent` and `rootline-gate` (agent and gate commits) | the App bot identity | SEC-080, SEC-081 |
| From O-5 (week 2, overview §5 PG-3) | the Fault Lab, with the `rootline-faultlab` installation token, pushing directly to `main`; from week 3 the same author pushes as the `protect-main` bypass actor | commit author `deploy-bot <deploy-bot@users.noreply.rootline.dev>` | LAB-022, SEC-080, SEC-081, PG-3 |
| Owner bypass | repository admin only, as the bypass actor of `protect-main` | owner git identity | SEC-081 |

Status: GitOps repository created 2026-11-26 with README commit 35d4916. Workload files `workload/*.yaml`, `.rootline/baseline.json` and tag `baseline-v1` arrive in W1-T09. Section `## GitOps repositories` is kept unchanged by W1-T12; other sections are added there.


## Prerequisites

Run `task doctor` in WSL from `/home/arkhash0309/projects/rootline`: every line must start with `OK` or `WARN` (a `WARN` for an `.env.local` key of a later week is expected). Required: native Docker Engine with at least 11.5 GiB of WSL memory (`.wslconfig` `memory=12GB`), `k3d` `5.9.0`, `kubectl`, `helm`, `task`, `uv`, `gh` logged in as `arkhash0309`, ports 80 and 443 free in WSL, and two deploy keys on the repositories `rootline` and `rootline-env` (overview §2 O-2).

## `.env.local` keys for week 1

| Key | Required in week 1 | Content |
|---|---|---|
| `DEPLOY_KEY_ROOTLINE` | yes | private OpenSSH deploy key of repository `arkhash0309/rootline`, quoted, multi-line |
| `DEPLOY_KEY_ROOTLINE_ENV` | yes | private OpenSSH deploy key of repository `arkhash0309/rootline-env`, quoted, multi-line |
| `ROOTLINE_ENV_DIR` | yes | `/home/arkhash0309/projects/rootline-env` |

`task secrets:local` (`scripts/secrets_local.py`) reads these keys. It creates namespaces `rootline-secrets` and `argocd`, Secret `rootline-secrets/rootline-bootstrap` (every non-empty key except `DEPLOY_KEY_*`, `ROOTLINE_ENV_DIR`, `ROOTLINE_HOST_ANTHROPIC_API_KEY`, `HF_USER`; empty in week 1) and the ArgoCD repository Secrets `argocd/deploy-key-rootline` and `argocd/deploy-key-rootline-env`. It never prints a value.

## `task up`

`task up` runs `scripts/up.py --revision develop` (`task up REVISION=<branch>` for another branch; the branch must exist on `origin`, because ArgoCD reads `git@github.com:arkhash0309/rootline.git`). Steps, each printed as `==> <name>`:

1. `k3d cluster`: creates cluster `rootline` from `infra/k3d/rootline.generated.yaml` (written from `infra/k3d/rootline.yaml`; git-ignored) when it does not exist.
2. `build and import images`: `scripts/build_images.py --tag dev --import-k3d rootline`; prints `no image has a Dockerfile yet: nothing to build` until a service has a `Dockerfile`.
3. `install ArgoCD`: Helm chart `argo/argo-cd` `10.20.0` (application `v3.6.3`) in namespace `argocd` with `deploy/upstream/argo-cd/values-local.yaml`, `--wait --timeout 10m`.
4. `secrets:local`: as above.
5. `apply root Application`: Application `root` (project `default`, path `deploy/root`, parameters `env=local`, `domain=127.0.0.1.sslip.io`, `targetRevision=<revision>`, automated sync with prune and selfHeal).
6. `wait for applications`: `scripts/wait_apps.py --timeout 1200` polls every 15 s; exit 1 prints the pending names and `kubectl -n argocd get applications`.
7. `ArgoCD login`: prints user `admin`, the password and the URL.
8. `memory check`: prints `memory_requests_total`.

Expected duration: the plan expects every Application Synced/Healthy within 20 min (W1-T12 Step 5). Measured 2026-11-27 on a cold Docker image cache: the k3d cluster started in about 1 min, the large images (Loki, Tempo, Prometheus) took about 2 min each to pull, and the first bring-up did not finish in 20 min because of the defects in [argocd](../components/argocd.md); a bring-up without those defects was not timed (unverified 2026-11-27).

## URLs and ArgoCD password

| Item | Value |
|---|---|
| ArgoCD UI | `https://argocd.127.0.0.1.sslip.io` (browser trusts the CA after `task trust-ca`) |
| User | `admin` |
| Password | `kubectl --context k3d-rootline -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' \| base64 -d` |

## Stop, start, remove

| Command | Effect |
|---|---|
| `task stop` | `k3d cluster stop rootline`; frees memory for Ollama; data stays |
| `task start` | `k3d cluster start rootline` |
| `task down` | `k3d cluster delete rootline`; keeps `.env.local` and `data/`; the node DNS workaround below must be applied again after the next `task up` |

## Verification results (W1-T12, 2026-11-27)

| Check | Command | Result |
|---|---|---|
| pgvector (DB-001) | `kubectl -n rootline-data exec rootline-pg-1 -- psql -U postgres -d rootline -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"` | `0.8.6` (the pinned `postgres-image` already contains pgvector; no custom image is needed) |
| Collector log permissions | `kubectl -n observability logs ds/otel-collector-agent \| grep -ci "permission denied"` | `0` |
| Prometheus pod label | `kubectl -n observability get pods -l app.kubernetes.io/name=prometheus -o name` | one pod |
| Operator pod label | `kubectl -n observability get pods -l app.kubernetes.io/name=kube-prometheus-stack-prometheus-operator -o name` | one pod |
| Gateway | `kubectl get gateway -A` | `kube-system/rootline` `PROGRAMMED=True`; listeners `http` and `https` Accepted, ResolvedRefs, Programmed |
| Memory (S2) | `task doctor` | `memory_requests_total=3.684 GiB` (cap 9.5), see [capacity](../components/capacity.md) |
| Applications | `kubectl -n argocd get applications` | 13 of 14 Synced/Healthy; `workload` Unknown (see [argocd](../components/argocd.md) D4) |
| `task trust-ca` and browser login (Step 7) | not run: `sudo` password prompt and the Windows certificate dialog need the owner | unverified (2026-11-27) |

The cluster checks ran at revision `fix/w1-t12-verify-scratch` (commit `17f2bd6`), not at `develop`, because `develop` has the root-chart defects D1 to D3 of [argocd](../components/argocd.md).

## Troubleshooting

| Symptom | Cause and command |
|---|---|
| Every Application `Unknown`; repo-server log `failed to list refs: dial tcp <ip>:22: connect: connection timed out` | The workstation DNS search domain resolves `github.com.<domain>` through a wildcard record (environment problem E1 in [argocd](../components/argocd.md)). Check `kubectl -n argocd exec deploy/argocd-repo-server -c repo-server -- getent hosts github.com` (must print a GitHub address, not `github.com.<domain>`). Workaround: `docker exec k3d-rootline-server-0 sh -c "grep -v '^search' /etc/resolv.conf > /tmp/r && cat /tmp/r > /etc/resolv.conf"`, then `kubectl -n argocd rollout restart deploy/argocd-repo-server deploy/argocd-server sts/argocd-application-controller` |
| Apps stuck `Progressing` or `OutOfSync` | `kubectl -n argocd get applications`; details with `kubectl -n argocd get application <name> -o jsonpath='{.status.conditions}{"\n"}{.status.operationState.message}'`; the same view is in the ArgoCD UI (Application, "Details", "Events") |
| A failed sync is not retried | `kubectl -n argocd annotate application <name> argocd.argoproj.io/refresh=hard --overwrite`; a sync stuck in `Running` on an old revision: `kubectl -n argocd patch application <name> --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'` |
| Pod `CreateContainerConfigError`, `secret "pg-..." not found` | ExternalSecrets of `platform-config` not synced; fix the Application first (the ExternalSecret webhook must have endpoints) |
