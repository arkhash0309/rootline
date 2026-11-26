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

