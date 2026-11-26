# Rootline Implementation Plan — Week 7: Cloud and Benchmark

> **For agentic workers:** Execute this week with the swarm protocol in `2026-11-26-rootline-00-overview.md` §7: the Haiku 5.5 coordinator runs the stages in the **Execution schedule** below, dispatching Sonnet 5.5 implementers (high effort, one worktree per task in parallel stages), Opus 5.5 reviewers (high effort) and, when re-planning is needed, the Opus 5.5 planner (high effort) — `CLAUDE.md` → "Agent models and roles". Within each task, follow superpowers:subagent-driven-development's discipline (implement → spec-compliance review → code-quality review). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducible, signed releases on GCP: a persistent Terraform root (state, artifacts, registry, WIF, budget) and an ephemeral cluster root that `task gke:up` turns into a working demo in ≤ 25 minutes and `task gke:down` removes completely; the full evaluation toolchain (report, judge, Langfuse sync, cost gate, ablations); sweep 1; the ITBench subset; T0 threshold calibration.

**Architecture:** Terraform reads `versions.yaml` with `yamldecode`. GitHub Actions authenticates to GCP only through Workload Identity Federation; `release.yml` on `main` builds, SBOMs, attests and keyless-signs images, and Kyverno enforces the signature on GKE. Secret values never pass through Terraform: `task gke:up` uploads them with `gcloud secrets versions add`.

**Tech Stack:** Terraform 1.x, `google` provider 7.x, `helm` and `kubectl` Terraform providers, GKE Standard (zonal, spot), Artifact Registry, GCS, Secret Manager, cosign, syft, Let's Encrypt (cert-manager HTTP-01 over Gateway API).

## Global Constraints

All constraints in `2026-11-26-rootline-00-overview.md` → "Global Constraints" apply. Week-specific additions:

- **Every GKE session ends with `task gke:down`**; the S1 leak checks must print empty lists. Record each session's start/end and cost in `wiki/log.md` and `wiki/cost-ledger.md`.
- Sweeps are owner-approved after the EVL-063 projection (O-13). Test-split results are viewed only in the final reports (EVL-011).
- Week 7 acceptance (MS-001): S1 achieved (≤ 25 min; teardown clean); sweep-1 report generated; cost ledger within plan.


## Execution schedule

Mirrors `2026-11-26-rootline-schedule.yaml` (week 7); `uv run python scripts/swarm_schedule.py table --week 7` must print exactly this table. Parallel stages run in separate worktrees (at most 3 implementers at once), then pass the integration gate (overview §7.6–§7.7) before one squash-merged PR reaches `develop`. Owned paths per task are listed in the YAML only. Deferred steps (overview §7.3) run at the start of the named sequential stage.

| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |
|---|---|---|---|---|
| W7-P1 | parallel | — | W7-T01 (`feat/w7-tf-persistent`); W7-T07 (`feat/w7-eval-complete`) | W7-T01 steps 3, 4 → W7-S1; W7-T01 pre-dispatch steps 1 (coordinator) |
| W7-P2 | parallel | W7-P1 | W7-T02 (`feat/w7-tf-cluster`); W7-T03 (`feat/w7-release`); W7-T10 (`feat/w7-calibrate-t0`) | W7-T03 steps 2 → W7-S1; W7-T10 steps 2, 3 → W7-S1 |
| W7-P3 | parallel | W7-P2 | W7-T04 (`feat/w7-kyverno-verify`); W7-T05 (`feat/w7-gke-tasks`); W7-T09 (`feat/w7-itbench`) | W7-T04 steps 2 → W7-S1; W7-T09 steps 3 → W7-S1 |
| W7-S1 | sequential | W7-P3 | W7-T06 (`docs/w7-gke-runbooks`); W7-T08 (no branch) | — |

---

### Task W7-T01: GCP bootstrap and the persistent Terraform root

**Requirement IDs:** INF-001 … INF-005, CI-010, PG-7, O-12.
**Depends on:** W6 complete. **Branch:** `feat/w7-tf-persistent`.

**Files:** `infra/terraform/persistent/{versions.tf,providers.tf,main.tf,wif.tf,budget.tf,variables.tf,outputs.tf,terraform.tfvars.example,backend.tf}`, `scripts/gke_bootstrap.py`, Taskfile `gke:bootstrap`, `wiki/runbooks/gcp-bootstrap.md`.

- [ ] **Step 1 [OWNER] (O-12):** create a GCP project (ID recorded only in the gitignored `terraform.tfvars` and `.env.gke`), link the billing account, `gcloud auth login` and `gcloud auth application-default login`, `gcloud config set project <id>`. Write each step into `wiki/runbooks/gcp-bootstrap.md` without the real IDs.
- [ ] **Step 2: Terraform**

```hcl
# versions.tf
locals { v = yamldecode(file("${path.root}/../../../versions.yaml")) }
terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }   # exact pin: see versions.yaml "google"; .terraform.lock.hcl committed
  }
}
```

Terraform cannot read `versions.yaml` inside the `terraform {}` block; `scripts/render_versions.py` therefore also writes `infra/terraform/{persistent,cluster}/versions.auto.tf` containing `required_providers { google = { source = "hashicorp/google", version = "= <versions.google>" } }` (and `helm`, `kubectl` for the cluster root), and `--check` covers them. `providers.tf`: `provider "google" { project = var.project_id, region = "us-central1", zone = "us-central1-a", default_labels = { project = "rootline", managed-by = "terraform", root = "persistent" } }`.

`main.tf` — exactly INF-004: `google_project_service` for each listed API (`disable_on_destroy = false`); buckets `rootline-tfstate-${var.project_id}` (versioning on) and `rootline-artifacts-${var.project_id}` (versioning off), both `location = "US-CENTRAL1"`, `uniform_bucket_level_access = true`, `public_access_prevention = "enforced"`, `force_destroy = false`; `google_artifact_registry_repository.rootline` (`repository_id = "rootline"`, `format = "DOCKER"`, cleanup policies: `keep` most recent 3 versions per package and `delete` untagged older than `86400s`).

`wif.tf`:

```hcl
resource "google_iam_workload_identity_pool" "github" { workload_identity_pool_id = "github" }
resource "google_iam_workload_identity_pool_provider" "actions" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == \"${var.github_repository}\""
}
locals { pool = google_iam_workload_identity_pool.github.name }

# Writer: only workflows running on refs/heads/main (release.yml) can push images.
resource "google_service_account" "ci" { account_id = "rootline-ci" }
resource "google_service_account_iam_member" "ci_wif_main" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${local.pool}/attribute.ref/refs/heads/main"
}
resource "google_artifact_registry_repository_iam_member" "ci_writer" {
  repository = google_artifact_registry_repository.rootline.name
  location   = "us-central1"
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci.email}"
}

# Reader: any workflow of the repository (eval-smoke.yml on PRs) can read smoke snapshots.
resource "google_service_account" "ci_read" { account_id = "rootline-ci-read" }
resource "google_service_account_iam_member" "ci_read_wif_repo" {
  service_account_id = google_service_account.ci_read.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${local.pool}/attribute.repository/${var.github_repository}"
}
resource "google_storage_bucket_iam_member" "ci_read_artifacts" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ci_read.email}"
}
```

INF-004 grants the registry writer only to the `refs/heads/main` principal set and the bucket reader to the whole repository. One service account cannot hold the two roles for two different principal sets, so the plan uses two accounts as above: `rootline-ci` (writer) and `rootline-ci-read` (reader). Repository variables: `GCP_WIF_PROVIDER`, `GCP_CI_SA` (writer, `release.yml`), `GCP_CI_READ_SA` (reader, `eval-smoke.yml`). Record the split in spec §26 and ADR 0018.

`budget.tf`: `google_billing_budget` (`billing_account = var.billing_account_id`, amount USD 15, thresholds 0.33/0.66/1.0 on `CURRENT_SPEND`, `all_updates_rule { disable_default_iam_recipients = false }`).

`outputs.tf`: bucket names, registry URL `us-central1-docker.pkg.dev/<project>/rootline`, WIF provider name, both SA emails.
- [ ] **Step 3: Bootstrap (INF-003)** — `task gke:bootstrap` → `scripts/gke_bootstrap.py`: writes gitignored `backend_override.tf` with `terraform { backend "local" {} }`, `terraform init && terraform apply`, then deletes the override, keeps the committed `backend.tf` (`terraform { backend "gcs" { prefix = "persistent" } }`, no bucket attribute because the name contains the project ID), runs `terraform init -migrate-state -force-copy -backend-config=bucket=<TF_STATE_BUCKET from .env.gke>`, and deletes `terraform.tfstate*`.
- [ ] **Step 4: Activate CI smoke (PG-7)** — set repository variables (`gh variable set GCP_WIF_PROVIDER ...` [CONFIRM]); upload smoke snapshots: `task lab:publish -- --only eval/smoke.yaml` (`scripts/lab_publish.py`: `gcloud storage cp` each `<run_id>.tar.zst` to `gs://<artifacts>/snapshots/v1/<scenario_id>/` and records `snapshot_uri` in `lab.scenario_runs`); then run `task lab:publish` for all captured snapshots (≈ 7.5 GB ⇒ ≈ USD 0.15/month storage, recorded in `cost-ledger.md`). Open a PR touching `prompts/` to confirm `eval / smoke` runs and passes. Remove the `notice` job's condition text from PR templates in `wiki/runbooks`.
- [ ] **Step 5: CI** — `infra` job now active: `terraform fmt -check`, `validate` (with `-backend=false`), `tflint`, `trivy config` pass. **Commit** `feat(infra): add persistent Terraform root with WIF, registry and budget`.

---

### Task W7-T02: Ephemeral cluster root, GKE values, domain and TLS

**Requirement IDs:** INF-010, INF-011, INF-012, INF-020 (gke params), INF-022 (gke image values), INF-040, INF-041, SEC-032 (gke issuer), SEC-011 (gke), ARC-031 (gke retention values).
**Depends on:** W7-T01. **Branch:** `feat/w7-tf-cluster`.

**Files:** `infra/terraform/cluster/{providers.tf,network.tf,gke.tf,iam.tf,secrets.tf,argocd.tf,variables.tf,outputs.tf,backend.tf}`, `deploy/upstream/*/values-gke.yaml` (complete), `deploy/upstream/traefik/values-gke.yaml`, `deploy/charts/platform-config/templates/letsencrypt.yaml`.

- [ ] **Step 1: Terraform** — resources exactly INF-010. Key settings:

```hcl
resource "google_container_cluster" "rootline" {
  name                     = "rootline"
  location                 = "us-central1-a"
  network                  = google_compute_network.vpc.id
  subnetwork               = google_compute_subnetwork.nodes.id
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false
  datapath_provider        = "ADVANCED_DATAPATH"
  release_channel { channel = "REGULAR" }
  workload_identity_config { workload_pool = "${var.project_id}.svc.id.goog" }
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  master_authorized_networks_config {
    cidr_blocks { cidr_block = var.admin_cidr, display_name = "owner" }
  }
  logging_config { enable_components = ["SYSTEM_COMPONENTS"] }
  monitoring_config { managed_prometheus { enabled = false } }
}
resource "google_container_node_pool" "spot" {
  name       = "spot"
  cluster    = google_container_cluster.rootline.id
  node_count = 2
  management { auto_repair = true, auto_upgrade = true }
  node_config {
    machine_type = "e2-standard-4"
    spot         = true
    disk_type    = "pd-balanced"
    disk_size_gb = 50
    shielded_instance_config { enable_secure_boot = true }
    workload_metadata_config { mode = "GKE_METADATA" }
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}
```

`iam.tf`: SAs `rootline-eso` (Secret Manager accessor on each secret below; WI binding `serviceAccount:<project>.svc.id.goog[external-secrets/external-secrets]`) and `rootline-seed` (bucket object viewer; WI binding for `[rootline/demo-seed]`); node SA gets `roles/artifactregistry.reader` on the repository. `secrets.tf`: one `google_secret_manager_secret` per Secret Manager ID in SEC-100 (`rootline-anthropic-api-key`, `rootline-langfuse-public-key`, `rootline-langfuse-secret-key`, `rootline-langfuse-host`, `rootline-gh-app-<agent|gate|faultlab>-<id|installation-id|private-key>`, `rootline-seed-<owner|interviewer|viewer1|breakglass|breakglass-otp-seed>`), `replication { auto {} }`, **no** `google_secret_manager_secret_version`. `argocd.tf`: `helm_release.argocd` (chart/version from `versions.yaml` via `local.v`, values file `deploy/upstream/argo-cd/values-gke.yaml`) and `kubectl_manifest.root_app` with the INF-010 parameters (`targetRevision: main`, `env=gke`, `domain=<ip-dashes>.sslip.io`, `gcpProject`, `k8sIssuer=https://container.googleapis.com/v1/projects/<project>/locations/us-central1-a/clusters/rootline`, `artifactsBucket`, `ingressIP`). Providers `helm` and `kubernetes`/`kubectl` configured from the cluster endpoint and `google_client_config` token. Variables: `project_id`, `admin_cidr`, `artifacts_bucket`, `registry`.
- [ ] **Step 2: GKE values** — upstream `values-gke.yaml` per chart (Traefik chart: `service.type: LoadBalancer`, `service.spec.loadBalancerIP: {{ingressIP}}` passed via the root chart parameter, `providers.kubernetesGateway.enabled: true`, `ports.websecure.tls.enabled: true`); ESO ClusterSecretStore `gcp` (`provider.gcpsm.projectID`, `auth.workloadIdentity.serviceAccountRef: {name: external-secrets, namespace: external-secrets}` with the KSA annotated `iam.gke.io/gcp-service-account: rootline-eso@<project>.iam.gserviceaccount.com`); ExternalSecrets switch store by `global.env`; umbrella `values-gke.yaml` with `image.registry: us-central1-docker.pkg.dev/<gcpProject>/rootline` and `image.tag` = `sha-<short revision>` (INF-022 — the root Application passes Helm parameter `image.tag=sha-$ARGOCD_APP_REVISION_SHORT`; verify ArgoCD substitutes `$ARGOCD_APP_REVISION_SHORT` in Helm parameters for the pinned version and record it; if not supported, `task gke:up` passes the short SHA of `origin/main` explicitly); `api` 2 replicas; retention per WKL-023.
- [ ] **Step 3: TLS (INF-041)** — ClusterIssuer `letsencrypt-prod` (ACME `https://acme-v02.api.letsencrypt.org/directory`, email from `.env.gke` `ACME_EMAIL` passed as a root parameter (never committed), solver `http01.gatewayHTTPRoute.parentRefs: [{name: rootline, namespace: traefik, kind: Gateway}]`); Certificate `rootline-tls` for `console.D`, `auth.D`, `argocd.D` (and `shop.D` when `expose.shop`), secret used by the Gateway HTTPS listener. Fallback parameter `tls.issuer=rootline-ca` switches the Certificate's issuer to the in-cluster CA chain (the W1 `ca.yaml` objects rendered for gke when `tls.issuer == "rootline-ca"`).
- [ ] **Step 4: Validate** — `terraform -chdir=infra/terraform/cluster init -backend=false && terraform validate`; `helm template` the root chart with `env=gke` through kubeconform. **Commit** `feat(infra): add ephemeral GKE cluster root and GKE values`.

---

### Task W7-T03: Release workflow (build, SBOM, attest, sign)

**Requirement IDs:** CI-001 (`release.yml`), CI-020, SEC-083, SEC-090 (signing side), T7.
**Depends on:** W7-T01. **Branch:** `feat/w7-release`.

- [ ] **Step 1: `.github/workflows/release.yml`**

```yaml
name: release
on: {push: {branches: [main]}}
permissions: {id-token: write, contents: read}
concurrency: {group: release, cancel-in-progress: false}
jobs:
  images:
    runs-on: ubuntu-24.04
    strategy:
      matrix: {image: [api, agent, gate, faultlab, mcp-k8s, mcp-telemetry, mcp-gitops, console]}
    env: {REGISTRY: "us-central1-docker.pkg.dev/${{ vars.GCP_PROJECT }}/rootline"}
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - id: auth
        uses: google-github-actions/auth@v2
        with: {workload_identity_provider: "${{ vars.GCP_WIF_PROVIDER }}", service_account: "${{ vars.GCP_CI_SA }}"}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
      - uses: astral-sh/setup-uv@v6
      - id: build
        run: |
          TAG="sha-${GITHUB_SHA::7}"
          uv run python scripts/build_images.py --only ${{ matrix.image }} --tag "$TAG" --push "$REGISTRY" --digest-file digest.txt
          echo "ref=$REGISTRY/${{ matrix.image }}@$(cat digest.txt)" >> "$GITHUB_OUTPUT"
      - uses: sigstore/cosign-installer@v3
        with: {cosign-release: "v${{ env.V_COSIGN }}"}
      - uses: anchore/sbom-action@v0
        with: {image: "${{ steps.build.outputs.ref }}", format: spdx-json, output-file: sbom.spdx.json, syft-version: "v${{ env.V_SYFT }}"}
      - run: cosign attest --yes --type spdxjson --predicate sbom.spdx.json "${{ steps.build.outputs.ref }}"
      - run: cosign sign --yes "${{ steps.build.outputs.ref }}"
      - run: echo "| ${{ matrix.image }} | \`${{ steps.build.outputs.ref }}\` |" >> "$GITHUB_STEP_SUMMARY"
```

`build_images.py --push <registry>` builds with `--provenance=false`, pushes `<registry>/<image>:<tag>`, labels `org.opencontainers.image.revision=$GITHUB_SHA` and `created`, writes the pushed digest; `GCP_PROJECT` is a repository variable [CONFIRM]. The release never pushes commits (SEC-083).
- [ ] **Step 2: Verify** — after the next `release: milestone` merge: `cosign verify --certificate-identity "https://github.com/arkhash0309/rootline/.github/workflows/release.yml@refs/heads/main" --certificate-oidc-issuer https://token.actions.githubusercontent.com <ref>` succeeds; `cosign verify-attestation --type spdxjson ...` succeeds. Record in `wiki/security/threat-model.md` (T7 evidence). **Commit** `ci: add signed release workflow`.

---

### Task W7-T04: Kyverno image verification on GKE

**Requirement IDs:** SEC-090 (`verify-rootline-images` Enforce on gke), T7.
**Depends on:** W7-T03, W3-T12.

- [ ] **Step 1: Policy and offline test** — `policies/kyverno/verify-rootline-images.yaml`: `verifyImages` rule for `us-central1-docker.pkg.dev/{{gcpProject}}/rootline/*` with keyless attestor `subject: https://github.com/arkhash0309/rootline/.github/workflows/release.yml@refs/heads/main`, `issuer: https://token.actions.githubusercontent.com`, `rekor: {url: https://rekor.sigstore.dev}`, `mutateDigest: true`, `verifyDigest: true`, `validationFailureAction: Enforce`; rendered only for gke. Kyverno test with a signed and an unsigned reference using a recorded `imageVerify` response; if `kyverno test` cannot verify signatures offline on the pinned CLI, the test is marked `gke-only` in `policies/kyverno/tests/verify-rootline-images/README.md` and step 2 is its verification. **Commit** `feat(policies): enforce signed Rootline images on GKE`.
- [ ] **Step 2: Live check on GKE** (deferred to W7-S1, during W7-T06): push an unsigned tag manually, `kubectl run unsigned -n rootline --image=us-central1-docker.pkg.dev/<p>/rootline/api:unsigned-test` → denied; record the output in `wiki/security/threat-model.md` (T7).

---

### Task W7-T05: `task gke:up` / `gke:down`, secrets upload, demo seed

**Requirement IDs:** GEN-060 (`gke:up`, `gke:down`), INF-012, INF-050, INF-051, SEC-100 (gke), PG-9, S1.
**Depends on:** W7-T02. **Branch:** `feat/w7-gke-tasks`.

- [ ] **Step 1: `scripts/gke_up.py`** — in order: read `.env.gke`; detect `admin_cidr` from `https://api.ipify.org` (`<ip>/32`); `terraform apply -auto-approve -var ...` in `infra/terraform/cluster` with backend config from `.env.gke`; `gcloud container clusters get-credentials rootline --zone us-central1-a`; for each SEC-100 Secret Manager ID: `gcloud secrets versions add <id> --data-file=-` with the value on stdin (skip when the latest version already equals the value — compare SHA-256 via `gcloud secrets versions access latest`); create ArgoCD repository Secrets directly (PG-9); wait ≤ 20 min for all Applications `Synced/Healthy` (`wait_apps.py --context gke_...`); wait ≤ 10 min for Certificate `rootline-tls` Ready, otherwise apply the INF-041 fallback (patch root param `tls.issuer=rootline-ca`, print `task trust-ca -- --env gke` instructions, append to `wiki/log.md`); print URLs `https://console.<D>`, `https://auth.<D>`, `https://argocd.<D>` and the ArgoCD admin password; print elapsed time since start (S1).
- [ ] **Step 2: `scripts/gke_down.py`** — exactly INF-012 steps 1–4; step 4 prints the four S1 lists plus `gcloud compute disks list --filter="name~^pvc-"`, and deletes orphaned PVC disks after an interactive `y/N` confirmation; exits non-zero if any list is non-empty after cleanup.
- [ ] **Step 3: Demo seed (INF-050/051)** — `task seed:export` → `scripts/seed_export.py`: `pg_dump --data-only` via `kubectl exec` on the local CNPG pod for the INF-050 tables, filtered to the incidents in `deploy/values/showcase-incidents.yaml` (owner picks 3 incident IDs) using `COPY (SELECT …) TO STDOUT` per table in dependency order (`core.incidents`, `core.alerts`, `core.jobs`, `core.investigations`, `core.investigation_events`, `core.steps`, `core.tool_calls`, `core.llm_calls`, `core.reports`, `core.proposals`, `core.approvals`, `audit.log` rows whose `target` refers to those objects plus all rows needed to keep the chain contiguous from id 1 — the export takes **all** `audit.log` rows up to the last relevant ID so the chain verifies), zstd-compressed to `seed.sql.zst`, uploaded to `gs://<artifacts>/seed/v1/seed.sql.zst`. `demo-seed` Job (gke, wave 2, KSA `rootline/demo-seed` with WI): if `SELECT count(*) FROM core.incidents` = 0 → download, `psql` as `rootline_migrator` with `SET session_replication_role = replica` for FK ordering, `SELECT setval(...)` for `audit.log_id_seq`, then `rootline audit verify` must report `chain_ok`; exit 1 otherwise.
- [ ] **Step 4: Commit** `feat(infra): add gke:up/gke:down tasks and demo seed`.

---

### Task W7-T06: GKE spin-up runbook and S1 timing

**Requirement IDs:** S1, INF-011, R9, R10, `wiki/runbooks/gke-spin-up.md`, `gke-teardown.md`.
**Depends on:** W7-T03 … W7-T05.

- [ ] **Step 1 [PAID ≈ USD 0.20 GCP]:** with a fresh `release: milestone` image set on `main`, run `task gke:up` with a stopwatch; then the demo checklist: log in as `owner` with a new passkey (SEC-021 note), view seeded incidents, run one Fault Lab demo (`scn-v1-git-bad-image-tag-00`) end to end [PAID ≈ USD 0.15 LLM], verify Kyverno blocks an unsigned image (W7-T04); `task gke:down`; leak checks empty.
- [ ] **Step 2:** write both runbooks with exact commands, expected durations per phase (Terraform ≈ 8 min, ArgoCD sync ≈ 10 min, TLS ≈ 2 min), troubleshooting (spot preemption → node pool recreates; LE failure → fallback), and the measured total; record cost per hour vs INF-011 in `cost-ledger.md`. Acceptance S1: total ≤ 25 min and clean teardown.

---

### Task W7-T07: Evaluation toolchain completion

**Requirement IDs:** EVL-001 (judge, langfuse-sync, report), EVL-031, EVL-040, EVL-041, EVL-042, EVL-050, EVL-051, EVL-063, EVL-070, EVL-071, EVL-090, UI-040 (PNG/SVG charts).
**Depends on:** W4-T12. **Branch:** `feat/w7-eval-complete`.

- [ ] **Step 1: Ablations (EVL-042)** — `--ablation no-preprocessing`: the replay servers are built with `ablation="no-preprocessing"` so `search_logs` returns `{total_lines, lines: [first 200 matching lines ≤ 300 chars]}` (output model variant), `get_metric_series` and `find_anomalies` omit anomalies/change points and `find_anomalies` returns top-25 (service, metric) by `|last − baseline_median| / max(|baseline_median|, ε)`; prompts are unchanged; `--ablation no-verifier`: `verify` computes its result but `passed` is forced true (record `would_have_failed`); `--memory on` (W5-T06). Tests per ablation on the fixture snapshot.
- [ ] **Step 2: Cost gate (EVL-063)** — `run_sweep` with `--sweep-plan eval/sweeps/sweep1.yaml` (list of `{config, split, ablation?, memory?}` entries) computes `Σ n × pilot_mean_cost(config) × 0.5` (`all-large` = `routed × 2.0` unless measured; `baseline` and `local` = 0) from `wiki`-independent data stored in `eval/pilots/pilot-cost-<config>.json` (written by W4-T14), compares with `eval.cap − eval.spent` from the ledger, and if over prints the four-step reduction plan and exits 2; flags `--skip-ablation <name>`, `--effort-override node=effort,...` (applies to `routed`/`all-large`), `--skip-config <name>`.
- [ ] **Step 3: Judge (EVL-050/051)** — prompt `prompts/judge_explanation.v1.md` (rubric anchors 1–5 for clarity, actionability, evidence_use; output `JudgeScore {clarity:int(1–5), actionability:int(1–5), evidence_use:int(1–5), rationale:str(≤300)}`); `rootline-eval judge <run_id>` judges routed diagnosed reports with `claude-sonnet-5-5` / low via the batch backend; `rootline-eval judge --human-labeling <dev run_id>` terminal UI (prompt_toolkit-free: plain `input()` loop) shows one report at a time (summary, claims, evidence previews, label) and records owner scores to `eval/judge/human-<run_id>.jsonl`; `rootline-eval judge --agreement <dev run_id>` computes quadratic-weighted Cohen's κ per dimension (`sklearn.metrics.cohen_kappa_score(weights="quadratic")` — add scikit-learn to `versions.yaml`) on the 50 overlapping reports; κ < 0.4 marks the dimension "judge unreliable" in the report.
- [ ] **Step 4: Langfuse sync (EVL-070/071)** — `--init-dataset` creates dataset `rootline-bench-v1` with one item per scenario (input, expected output, metadata per EVL-070) idempotently (item ID = scenario ID); `langfuse-sync <run_id>` creates dataset run `<run_id>-<config>`, links each sampled-in scenario's trace (trace ID = `ulid_to_trace_id(investigation_id)`), attaches the EVL-071 scores; respects OBS-021 sampling and the unit counter.
- [ ] **Step 5: Full report (EVL-090)** — `report <run_id>…` writes all ten sections in order; charts via matplotlib to PNG and SVG (`eval/reports/<group_id>/charts/{pareto,categories,reliability_<config>,confusion_<config>}.{png,svg}`); McNemar + Holm between `routed` and every other config (EVL-040); "better"/"worse" wording only when Holm p < 0.05, else "no significant difference" (unit test over the wording function); failure-analysis section reads owner labels from `eval/failure-modes/<run_id>.yaml` (`{scenario_id: mode}` with the fixed list; missing labels render "unlabelled" and fail `report --final`); limitations section is copied from `eval/limitations.md` (owner-written); per-category/channel/held-out tables with n (EVL-031); cost table with list-price equivalents.
- [ ] **Step 6: Commit** `feat(eval): add ablations, cost gate, judge, Langfuse sync and full report`.

---

### Task W7-T08: Sweep 1

**Requirement IDs:** EVL-060 (sweep 1), EVL-041, EVL-042, EVL-062, EVL-063, S4 (partial), O-13.
**Depends on:** W7-T07, capture complete.

- [ ] **Step 1:** write `eval/sweeps/sweep1.yaml`: `baseline`, `all-small`, `routed`, `local` on `test`; `all-large` and the three ablations (`no-preprocessing`, `no-verifier`, `memory-on`) on `test-half`.
- [ ] **Step 2 [PAID, projected by EVL-063 ≈ USD 35] (O-13):** `task eval:sweep -- --sweep-plan eval/sweeps/sweep1.yaml --batch` with `ROOTLINE_FINAL_SWEEP=1`; it prints the projection and waits for confirmation `yes`; on refusal follow the reduction plan. `local` runs separately interactive with the cluster stopped: `task stop` then `rootline-eval run --config local --split test`.
- [ ] **Step 3:** `rootline-eval report <all sweep-1 run IDs>` → `eval/reports/sweep1/report.md`; `rootline-eval judge <routed run>`; `rootline-eval langfuse-sync <run>` per run; export and import runs into the local `api` (`POST /v1/eval/runs/import`) so the console shows them. Update `wiki/eval/results.md` and `cost-ledger.md`.

---

### Task W7-T09: ITBench external subset (cut item 1)

**Requirement IDs:** EVL-110, MS-003 (cut order).
**Depends on:** W7-T07. **Branch:** `feat/w7-itbench`.

- [ ] **Step 1:** clone `itbench-hub/ITBench-Scenarios` (licence Apache-2.0 re-verified; record the commit SHA in `eval/runner/rootline_eval/itbench/SOURCE.md`); list SRE scenarios targeting the OpenTelemetry Astronomy Shop; select up to 30 compatible with the trimmed workload (all referenced services kept, no removed component involved) in the order they appear in the repository; record selection reasons in `itbench/selection.yaml`.
- [ ] **Step 2:** adapter `itbench/run.py`: for each scenario, apply its fault injection to `shop` (translate its manifests/commands into kubectl actions executed by faultlab's `Kube` adapter; namespaces rewritten to `shop`), then run the standard capture timeline (LAB-041 steps 3–8, `parity: true`), and map ground truth to a `ScenarioLabel` with `dataset_version: "v1"`, `scenario_id: "itb-<id>"`, `category` via `itbench/mapping.yaml`, `acceptable_actions: []`, split `test`.
- [ ] **Step 3:** sweep `routed`, `all-small`, `baseline` on the ITBench labels (scoring `top1`, `top3`, `category_acc`, cost only) [PAID ≈ USD 2]; report section "External check (ITBench subset, n=<n>)" with the EVL-110 caveat; fewer than 10 compatible scenarios → write the explanation and record the cut (ADR).

---

### Task W7-T10: T0 threshold calibration

**Requirement IDs:** EVL-061, POL-030, ADR 0008.

- [ ] **Step 1: Code and unit test** — `rootline-eval calibrate-t0 <run_id>` computes, for v ∈ {0.70, 0.75, 0.80, 0.85, 0.90, 0.95}, among dev results with `confidence ≥ v` and a T0-eligible action type (`revert_commit`, `resync_app`, `restart`) the share with `fix_acceptable`; picks the smallest v with share ≥ 95% and ≥ 10 such results, else 0.95; prints the table; with `--write` writes `deploy/values/policy.yaml` `t0ConfidenceThreshold: <v>`. Unit test on synthetic results covering a qualifying value, the ≥ 10 rule and the 0.95 fallback. Commit `feat(eval): add T0 confidence threshold calibration`.
- [ ] **Step 2: Calibrate** (deferred to W7-S1) on the latest dev `routed` run (the dev iteration before sweep 2): `rootline-eval calibrate-t0 <run_id> --write`; add the table to ADR 0008; commit on `feat/w7-calibrate-t0-deferred`.
- [ ] **Step 3: Week 7 acceptance and release** (deferred to W7-S1, after W7-T08): acceptance checks and `release: milestone 7`.
