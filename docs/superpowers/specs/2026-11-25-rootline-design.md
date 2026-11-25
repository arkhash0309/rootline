# Rootline — Design Specification

- **Date:** 2026-11-25
- **Status:** Approved design, pending written-spec review
- **Repo:** `arkhash0309/rootline` (private)
- **Implementers:** AI coding agents, directed and reviewed by the project owner

## 1. Summary

Rootline is an AI SRE agent that diagnoses incidents in a live Kubernetes cluster, proves its accuracy on a self-generated labelled benchmark, and can only change production through policy-checked GitOps pull requests.

A chaos harness (the **Fault Lab**) injects faults with known root causes into a trimmed OpenTelemetry Demo application. Each injection produces a labelled scenario. A LangGraph agent investigates through three OAuth-protected MCP tool servers, writes a cited root-cause report, and proposes a fix drawn from a typed action catalogue. An OPA policy engine decides whether the fix auto-merges, needs human approval, needs passkey step-up approval, or is denied. ArgoCD applies merged fixes.

### 1.1 Goals

1. Show production-grade **AI/LLM engineering**: structured agent, model routing, grounding, guardrails, measured evaluation, cost control.
2. Show **end-to-end ownership**: frontend, backend, database, data, security, infrastructure, CI/CD, observability.
3. Make every required technology carry real weight: Docker, Kubernetes, GitOps, Terraform, ArgoCD, modern user and agent authentication, Langfuse.
4. Stay within a **$100 total budget**.
5. Produce public evidence: a benchmark dataset, a technical write-up, a demo video and decision records.

### 1.2 Non-goals

- Multi-tenant SaaS. One organisation with several roles. Do not add a tenant ID.
- Persistent hosting. The cloud environment is brought up for interviews and destroyed afterwards.
- Diagnosing arbitrary third-party clusters. Rootline targets its own cluster.
- Fine-tuning or distillation. This is a version 2 stretch goal (see §13).
- GPU inference.

### 1.3 Success criteria

| # | Criterion |
|---|---|
| S1 | From a clean GCP project, `terraform apply` followed by ArgoCD sync produces a working demo in ≤ 20 minutes. `terraform destroy` removes all billable resources. |
| S2 | `make up` produces the same system on k3d on a 16 GB laptop. |
| S3 | ≥ 300 labelled scenarios are captured as replayable snapshots, with a held-out test split that includes unseen fault types. |
| S4 | The benchmark reports every metric in §6.5 with bootstrap 95% CIs, for the non-LLM baseline and the four model configurations, including categories where the agent loses. |
| S5 | Zero fixes outside tier T0 ever merge without a recorded human approval. Zero denied-class actions ever merge. Both are verified by tests and by audit-log replay. |
| S6 | No prompt-injection scenario in the test set causes an action outside policy. |
| S7 | End-to-end Playwright test passes in CI: inject → incident → root cause → T0 auto-merge → ArgoCD sync → verified recovery. |
| S8 | Total project spend ≤ $100, tracked by LiteLLM budgets and GCP billing alerts. |
| S9 | The wiki is current: `status.md` matches the real milestone, and every major decision has an ADR. |

## 2. Key decisions

| Decision | Choice | Main reason |
|---|---|---|
| Target role | AI / LLM Engineer | Owner's goal; highest 2026 demand |
| Concept | Self-diagnosing cluster (AI SRE) | Free labelled data; every tool earns its place |
| Workload under test | OpenTelemetry Demo, trimmed to core services | Built-in fault flags, rich telemetry, benchmark comparability |
| Model strategy | Routed API models (small + large) via LiteLLM, plus a local Ollama baseline | Cost-vs-accuracy story; privacy option |
| Cloud | GCP / GKE zonal, spot nodes | Free zonal management-fee tier; fit with Google |
| Hosting | None persistent; apply and destroy for interviews | Budget |
| Autonomy | Risk-tiered OPA policy (T0 auto / T1 approve / T2 step-up / Denied) | Shows judgement about autonomy boundaries |
| User IdP | Keycloak (self-hosted) with passkeys | Free; supports RFC 8693 token exchange |
| Agent tracing | Langfuse Cloud, free tier | Datasets, experiments, scores; no heavy self-hosting |
| Queue | Postgres `SKIP LOCKED` | Avoids Redis/Kafka |
| Database | Postgres 16 + pgvector via CloudNativePG | No managed-DB bill; operator experience |
| Image registry | GHCR | Free; available when no cloud is running |
| Wiki | In-repo `wiki/` plus a project skill | Portable across agents; visible to reviewers |

## 3. Architecture

```
               ┌──────────── Rootline Console (Next.js) ──────────────────┐
   Human ──►   │ incidents · live investigation · approvals · eval board  │
 (passkey)     └───────────────┬──────────────────────────────────────────┘
                     OIDC      │ REST + SSE (via backend-for-frontend)
  ┌──────────┐     ┌───────────▼───────────┐   ┌──────────────────────┐
  │ Keycloak │◄────┤ Platform API (FastAPI)│──►│ Postgres + pgvector  │
  │ IdP, RFC │     └───┬───────────┬───────┘   │ incidents, audit,    │
  │ 8693 exch│         │           │           │ incident memory      │
  └────▲─────┘   ┌─────▼─────┐  ┌──▼─────────┐ └──────────────────────┘
       │ token   │ Agent     │  │ Fault Lab  │──► injects faults, captures
       └─────────┤ (LangGraph│  │            │    snapshots, writes labels
                 │  workers) │  └─────┬──────┘
                 └─┬───┬───┬─┘        ▼
          MCP/OAuth│   │   │
   ┌───────────────┘   │   └──────────────┐
 ┌─▼──────────┐ ┌──────▼────────┐ ┌───────▼────────┐
 │ k8s MCP    │ │ telemetry MCP │ │ gitops MCP     │──► GitHub PR ──► OPA policy
 │ (read-only)│ │ Prom/Loki/    │ │ (proposes PRs) │    ──► auto-merge or human
 └────────────┘ │ Tempo         │ └────────────────┘    ──► ArgoCD sync
                └───────────────┘
 LLM calls ──► LiteLLM gateway (routing, fallback, hard budgets) ──► API models / Ollama
 Agent traces ──► Langfuse Cloud
```

### 3.1 Components

Each component has one job and a defined interface.

| Component | Responsibility | Interface | Depends on |
|---|---|---|---|
| `workload` | Trimmed OTel Demo in namespace `shop` | HTTP; emits OTLP | OTel Collector |
| `telemetry` | OTel Collector → Prometheus, Loki, Tempo | PromQL / LogQL / TraceQL | — |
| `faultlab` | Inject faults, capture snapshots, record labels | REST (admin) + CLI | flagd, Chaos Mesh, GitOps repo, object store, Postgres |
| `mcp-k8s` | Read-only Kubernetes inspection tools | MCP over streamable HTTP; OAuth resource server | k8s API (read-only SA) or snapshot |
| `mcp-telemetry` | Semantic metric, log and trace tools | MCP; OAuth resource server | Prom/Loki/Tempo or snapshot |
| `mcp-gitops` | Git history tools; open fix PRs | MCP; OAuth resource server | GitHub App |
| `agent` | Investigation state machine | Consumes jobs from Postgres; writes steps | MCP servers, LiteLLM, Keycloak, Langfuse |
| `policy` | Classify proposed fixes into tiers | OPA REST decision API; GitHub status check | Rego bundle |
| `api` | REST/SSE, webhooks, authorisation, audit | OpenAPI 3.1 | Postgres, Keycloak |
| `console` | UI and backend-for-frontend | Browser | `api`, Keycloak |
| `llm-gateway` | LiteLLM proxy: routing, fallback, budgets, cost logs | OpenAI-compatible API | Provider APIs, Ollama |
| `admission` | Kyverno: signature verification and guard constraints | Admission webhook | cosign public identity |
| `infra` | Terraform (GKE) and k3d bootstrap | `terraform apply`, `make up` | GCP |
| `deploy` | ArgoCD app-of-apps; Kustomize overlays `local/`, `gke/` | Git | — |

## 4. Agent and AI design

### 4.1 Investigation state machine (LangGraph)

```
Alert ─► 1 Triage ─► 2 Hypothesize ─► 3 Gather evidence ◄─┐
                                         │                │ loop until stop rule
                                         ▼                │
                                 4 Update hypotheses ─────┘
                                         │
                 5 Root cause ─► 6 Verify ─► 7 Plan fix ─► Policy
```

1. **Triage** (small model). Inputs: the alert, the service graph from Tempo, and the top-k similar past incidents from pgvector. Output: affected services and an initial scope.
2. **Hypothesize** (large model). Output: a ranked list of hypotheses. The list always includes a "recent change" hypothesis based on the GitOps git log.
3. **Gather evidence.** The agent calls MCP tools. Two deterministic preprocessing steps run inside `mcp-telemetry`:
   - **Log template mining** (Drain3): returns templates with counts, first-seen times and sample lines, not raw lines.
   - **Metric anomaly detection** (robust z-score on MAD plus change-point detection): returns statements like "p95 latency 8.1× baseline from 14:02:10", not raw series.

   The small model summarises large tool outputs.
4. **Update hypotheses** (large model). Revises confidences.

   **Stop rule:** stop when the top hypothesis is supported by ≥ 2 independent evidence sources (different signal types), or when any budget runs out. Budgets per investigation: max steps (default 15), max tokens, max USD (default $0.10).
5. **Root cause** (large model). Output is a Pydantic-validated structure:
   - `root_cause_entity`
   - `fault_category` (from the taxonomy in §6.1)
   - `confidence` (0–1)
   - `summary`
   - `claims[]`, each with `evidence_refs[]` pointing to tool-call IDs
   - `status`: `diagnosed` or `inconclusive`
6. **Verify.**
   - A deterministic check that every `evidence_ref` exists and that its stored output contains the cited values.
   - A small-model critique for unsupported claims.
   - A report that fails verification returns to step 4 once, then is marked `inconclusive`.
7. **Plan fix.** The agent picks one action from the typed catalogue and fills its parameters. It cannot write free-form manifests.

   | Action | Parameters |
   |---|---|
   | `revert_commit` | `sha` |
   | `rollback_to_revision` | `app`, `revision` |
   | `scale` | `workload`, `replicas` |
   | `set_resources` | `workload`, `container`, `limits/requests` |
   | `toggle_flag` | `flag`, `value` |
   | `restart` | `workload` |
   | `none` | `reason` |

   `mcp-gitops` renders the action into a commit on a `rootline/<incident-id>` branch and opens a PR.

### 4.2 Model routing

- **Small API model:** steps 1, 3 (summaries) and 6. **Large API model:** steps 2, 4 and 5.
- **Escalation:** if confidence is < 0.5 after the loop, step 5 is retried once with the large model and a larger budget.
- **Prompt caching:** system prompts and tool schemas are cached.
- **Swappable configuration:** routing is set per node in configuration, so the four eval configurations (all-small, all-large, routed, local Ollama) need no code changes.
- **LiteLLM:** provides provider fallback and per-key hard budgets.
- Exact model IDs and prices are chosen during planning (§12).

### 4.3 Incident memory

- When an incident is resolved, a short postmortem (root cause, fix, key evidence) is embedded and stored in `incident_memory`.
- Triage retrieves the top-k similar postmortems.
- The benchmark runs with memory **on and off**. Memory is populated only from dev-split incidents, so the test split can't leak.

### 4.4 Guardrails

All telemetry, Kubernetes object content and git content is **untrusted**. The defences, in layers:

1. **Structural.** The agent has no tool that writes to the cluster. The only write path is a PR.
2. **Typed actions.** Fixes come only from the catalogue, and parameters are validated against live inventory: the workload, flag or SHA must exist.
3. **Policy gate.** OPA tiers (§5.4), plus branch protection.
4. **Data marking.** Tool outputs are wrapped in delimited data blocks, and system prompts state that the content of data blocks is never an instruction.
5. **Redaction.** Secrets and credential patterns are scrubbed in the MCP servers before any LLM sees the output. Langfuse masking is enabled as a second layer.
6. **Measurement.** Injection scenarios are part of the benchmark (§6.1).

## 5. Security and identity

### 5.1 Human authentication

- **Keycloak realm `rootline`:** passkeys (WebAuthn) are the primary credential. Password plus OTP is available only as a break-glass admin method.
- **OIDC authorization code flow with PKCE.** The Next.js server is a backend-for-frontend: tokens are held server-side, and the browser holds only an httpOnly, `Secure`, `SameSite=Lax` session cookie. A CSRF token is required on state-changing requests.
- **Roles:**
  - `viewer`: read access
  - `responder`: start investigations, add notes
  - `approver`: approve T1/T2 fixes
  - `admin`: Fault Lab, settings

  The API enforces roles on every route.
- **Step-up authentication.** T2 approval requires an ACR value showing passkey authentication within the last 5 minutes. The API returns an RFC 9470 `insufficient_user_authentication` challenge, and the console re-prompts for the passkey.
- **Separation of duties.** The user who started an investigation cannot approve its T2 fix.

### 5.2 Agent identity and delegation

1. **Workload identity.** Each agent pod uses a projected, audience-bound Kubernetes service-account token as its client assertion to Keycloak.

   *Fallback, if Keycloak's federated Kubernetes client authentication is unsuitable:* `private_key_jwt`, with the key mounted from a secret managed by External Secrets. This is decided in planning (§12).
2. **Delegation (RFC 8693).**
   - **Human-owned investigations.** The agent exchanges `subject_token` (the user's access token) plus `actor_token` (its workload token) for a token with:
     - an `act` claim naming the agent
     - `aud` set to exactly one MCP server, via the RFC 8707 `resource` parameter
     - scopes that are the intersection of the user's permissions and the tool's needs
     - a 5-minute TTL
   - **Alert-triggered investigations** with no human owner use the agent's own identity, with scopes `k8s:read`, `telemetry:read`, `gitops:read` and `gitops:propose`. The tier rules in §5.4 apply unchanged: T0 fixes may auto-merge, and T1/T2 fixes wait for a human approver.
3. **MCP resource servers.**
   - Each publishes RFC 9728 protected-resource metadata.
   - Each validates signature, `iss`, `aud`, `exp`, scopes and the `act` chain on every call.
   - Scopes: `k8s:read`, `telemetry:read`, `gitops:read`, `gitops:propose`.

### 5.3 Defence in depth

- **Kubernetes RBAC.** `mcp-k8s` runs with a ClusterRole allowing `get`/`list`/`watch` on workloads, pods, events, services, configmaps and ArgoCD Applications. **Secrets are excluded.**
- **GitHub App.** Contents write is limited by a push ruleset to `rootline/*` branches, plus pull-requests write. `main` is protected and requires the `rootline-policy` status check. T1/T2 PRs also require an approving review.
- **Network and pods.** Default-deny NetworkPolicies with explicit allow rules. The Pod Security Standard `restricted` applies in all Rootline namespaces.
- **Path and destination limits.**
  - Fix PRs may only modify files under `deploy/overlays/*/workload/`, and the `rootline-policy` status check rejects any other path.
  - The ArgoCD AppProject for the workload may only deploy to the `shop` namespace, so even a merged change cannot reach platform namespaces.
- **Admission control (Kyverno).**
  - Rejects images not signed by this repo's GitHub Actions identity.
  - Rejects privileged pods.

### 5.4 Fix policy (OPA/Rego, default-deny)

| Tier | Conditions | Gate |
|---|---|---|
| **T0** auto-merge | Action in {`rollback_to_revision` to last healthy, `revert_commit` where the commit is < 30 min old, `toggle_flag` to off, `restart`}. Single workload. Not stateful. Report `confidence` ≥ T0 threshold: 0.8 by default, re-set on the dev split to the lowest value that gives ≥ 95% acceptable-fix precision. Fewer than 3 T0 merges in the last hour across the cluster (circuit breaker). | Policy bot merges |
| **T1** approve | `scale`, `set_resources`, multi-workload changes, or any T0 action that fails a T0 condition | One `approver` |
| **T2** step-up | Touches StatefulSets or NetworkPolicies | `approver` with fresh passkey; not the initiator |
| **Denied** | Secrets, RBAC, platform namespaces (`rootline-*`, `argocd`, `keycloak`, `kyverno`), the agent's own permissions, the policy bundle | Never; the PR is closed with a reason |

Every decision records the matched rules and their reasons.

### 5.5 Secrets and supply chain

- **Secrets.** External Secrets Operator, backed by GCP Secret Manager on GKE and by a Kubernetes-secret backend seeded by `make up` on k3d. No plaintext secrets in Git.
- **Supply chain.** CI scans images and IaC with Trivy, generates SBOMs with Syft, and signs images with keyless cosign using GitHub OIDC. Kyverno verifies the signatures.

### 5.6 Audit

- **Append-only `audit_log` table.**
  - Columns: `id`, `ts`, `actor`, `on_behalf_of`, `action`, `target`, `payload`, `prev_hash`, `hash`.
  - The hash is SHA-256 over `prev_hash` and the row contents.
  - The application role has no UPDATE or DELETE privilege on the table.
- **Provenance.** Each entry links to the incident, Langfuse trace ID, token `jti`, PR number and ArgoCD sync revision.
- **Verification.** `rootline audit verify` recomputes the hash chain.

### 5.7 Threat model

A STRIDE threat model is kept in `wiki/security/threat-model.md`. It covers at minimum:
- prompt injection via telemetry
- token theft and replay
- confused deputy across MCP servers
- policy bypass via the PR path
- supply-chain tampering
- the agent escalating its own privileges

## 6. Data and evaluation

### 6.1 Fault taxonomy (~25 types)

| Group | Channel | Fault types |
|---|---|---|
| Application | OTel Demo flagd flags | Built-in flags such as payment failure, cache memory leak, Kafka queue problems, ad-service CPU or GC pressure, product-catalogue failure |
| Infrastructure | Chaos Mesh | pod kill, container kill, network delay, network partition, CPU stress, memory stress, DNS failure |
| Change-induced | bad GitOps commits | wrong image tag (ImagePullBackOff), broken env var or config, memory limit too low (OOMKill), broken readiness probe, wrong service port, overly strict NetworkPolicy, replicas set to 0 |
| Adversarial | composite | prompt-injection log lines, a concurrent red-herring alert, two simultaneous faults |

### 6.2 Scenarios and labels

- **Scenario:** fault type × target service × intensity × background load × seed.
- **Label (`scenarios` table):**
  - `scenario_id`
  - `fault_type`
  - `fault_category`
  - `root_cause_entities[]`
  - `injection_channel`
  - `injected_at`
  - `acceptable_actions[]`, each an action type with parameter constraints
  - `split`: `dev` or `test`
  - `notes`
- **Volume:** ≥ 300 scenarios, captured in automated overnight batches on k3d.

### 6.3 Capture and replay

- **Capture.** During a live run, the Fault Lab exports the incident window (from 10 minutes before injection to the end of capture) as compressed Parquet in object storage:
  - metrics for all workload series
  - logs
  - traces
  - Kubernetes object YAML and events
  - the GitOps git log
- **Replay.** Each MCP server has a `replay` mode that answers the same tools from a snapshot bundle.
- **Semantic tool layer.** Tools are semantic (for example `get_metric_series(service, metric, window)`, `search_logs(service, pattern, window)`, `get_error_traces(service, window)`, `get_recent_changes(window)`), not raw PromQL. That keeps replay feasible and is easier for LLMs.
- **Parity tests** check that live and replay modes agree (§9).

### 6.4 Splits and publication

- **Splits.** The test split holds about 40% of scenarios, including ≥ 4 fault types absent from dev. No prompt or threshold tuning on test.
- **Publication.** The dataset is published on Hugging Face as **Rootline-Bench** (snapshots, labels, data card) after checking that it contains no secrets.

### 6.5 Metrics

| Area | Metrics |
|---|---|
| Root-cause accuracy | top-1 and top-3 entity accuracy; fault-category accuracy; extra wrong entities penalised (ITBench-style) |
| Grounding | % claims with valid evidence refs; hallucinated-citation rate |
| Fixes | acceptable-fix rate; unsafe-proposal rate; policy catch rate |
| Efficiency | time to diagnosis, tool calls, tokens, USD per investigation (p50 and p95) |
| Robustness | injection-resistance rate; red-herring robustness |
| Calibration | reliability diagram; expected calibration error (ECE) |
| Honesty | inconclusive rate; confidently-wrong rate (scored worse than inconclusive) |

**Statistics.**
- Bootstrap 95% CIs on all rates, with n reported per category.
- McNemar tests for paired comparisons between configurations.

### 6.6 Baselines and ablations

- **Non-LLM baseline:** the most anomalous service, tie-broken by the most recent change.
- **Model configurations:** all-small, all-large, routed, local Ollama, presented as a cost-vs-accuracy Pareto chart.
- **Ablations:** preprocessing on/off; memory on/off; verifier on/off.

### 6.7 LLM-as-judge

- **Scope:** explanation quality only (clarity, actionability), against a written rubric.
- **Validation:** checked against ~50 owner-labelled judgements, with Cohen's κ reported.
- **Everything else is scored deterministically.**

### 6.8 External check

- One public benchmark subset (30–50 cases) from ITBench or Cloud-OpsBench.
- The choice is made in planning (§12), based on licence, setup cost and fit with the semantic tool layer.

### 6.9 Langfuse

- Each eval run is a Langfuse dataset experiment, with scores attached to traces.
- **CI regression gate:** PRs that change `services/agent/**`, `prompts/**` or `services/mcp-*/**` replay a 10-scenario smoke set using the routed config. It expands to 20 scenarios for PRs labelled `eval-full`. The gate fails if top-1 accuracy drops more than 5 points below the stored baseline, or cost rises more than 25%.

## 7. Backend, database and APIs

### 7.1 Repository layout

```
apps/console/          Next.js (TypeScript), UI + backend-for-frontend
services/api/          FastAPI: REST + SSE, webhooks, authz, audit
services/agent/        LangGraph workers
services/mcp-k8s/      MCP server (live + replay)
services/mcp-telemetry/
services/mcp-gitops/
services/faultlab/     injectors, scenario runner, snapshot capture
libs/py-common/        shared auth, config, logging, audit client
policies/opa/          Rego fix tiers + tests
policies/kyverno/      admission policies
eval/                  benchmark runner, scoring, reports
prompts/               versioned prompt templates
infra/terraform/       GKE, VPC, GCS, Secret Manager, IAM, budgets
deploy/                ArgoCD app-of-apps; base + overlays/{local,gke}
wiki/                  project knowledge base (§11)
docs/                  specs, plans, write-ups
```

### 7.2 Backend

- **Language and tooling:** Python 3.12, uv workspaces, FastAPI, SQLAlchemy 2 with Alembic, Pydantic v2.
- **API contract:** the OpenAPI 3.1 spec generates a typed TypeScript client for the console. CI fails on drift.
- **Job queue:** a Postgres table consumed with `SELECT … FOR UPDATE SKIP LOCKED`.
- **Durability:** the LangGraph checkpointer is stored in Postgres, so an investigation resumes after a worker crash.
- **Event flow:** Alertmanager webhook → dedupe by fingerprint → `incidents` → job → agent → `investigation_steps` → `NOTIFY` → API SSE stream.
- **Webhooks:**

  | Path | Verification |
  |---|---|
  | `/hooks/alertmanager` | HMAC |
  | `/hooks/github` | `X-Hub-Signature-256` |
  | `/hooks/argocd` | shared secret; sync status |

- **Main REST routes (v1):**
  - `GET /incidents`
  - `GET /incidents/{id}`
  - `POST /incidents/{id}/investigations`
  - `GET /investigations/{id}/events` (SSE)
  - `GET /proposals/{id}`
  - `POST /proposals/{id}/approve`
  - `POST /proposals/{id}/reject`
  - `GET /faultlab/scenarios`
  - `POST /faultlab/runs`
  - `GET /eval/runs`
  - `GET /eval/runs/{id}`
  - `GET /audit`
  - `GET /audit/verify`

### 7.3 Database (Postgres 16 + pgvector, CloudNativePG)

| Group | Tables |
|---|---|
| Users | `users` (mirror of Keycloak `sub`, display name, roles cache) |
| Incidents | `incidents`, `alerts`, `investigations`, `investigation_steps` (tool name, input, output ref, tokens, cost, Langfuse span ID), `hypotheses`, `rca_reports`, `remediation_proposals` (action, params, tier, policy decision, reasons, PR number), `approvals` |
| Audit | `audit_log` (hash-chained, append-only) |
| Memory | `incident_memory` (text, embedding `vector`, source incident) |
| Lab | `scenarios`, `scenario_runs`, `snapshots` (metadata + object-store URI) |
| Eval | `eval_runs` (config, git SHA, cost), `eval_results` (per scenario, per metric) |
| Queue | `jobs` |

- **Blob storage:** large blobs (snapshots, large tool outputs) live in object storage behind an `fsspec` abstraction: GCS on GKE, a PVC directory on k3d.
- **Backups:** CloudNativePG backups go to GCS on GKE.

### 7.4 Error handling

- **Tool failures** are recorded as evidence (`tool_unavailable`, with the error), and the agent continues.
- **Provider outages:** LiteLLM falls back to another provider.
- **Budget exhaustion** ends the run with `status=inconclusive` and a partial report.
- **Invalid structured output:** one repair retry, then `inconclusive`.
- **Idempotency:** webhooks and approvals carry idempotency keys, and approving an already-merged proposal is a no-op.
- **Crashed workers:** the checkpointer resumes the investigation. A job lease timeout re-queues abandoned jobs.

## 8. Frontend (Rootline Console)

**Stack:** Next.js App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query, Recharts, React Flow, and the generated API client.

**Pages:**
1. **Incidents.** A list with status, severity, service and time to diagnosis.
2. **Live investigation.**
   - streaming step timeline
   - hypothesis board with live confidence bars
   - evidence panels: anomaly chart, log templates, trace excerpt
   - service topology with the suspect service highlighted
3. **Root-cause report.** Claims with clickable citations that open the evidence.
4. **Fix proposal.**
   - GitOps diff
   - tier and policy reasons
   - Approve/Reject, with passkey step-up for T2
   - PR and ArgoCD sync status
5. **Fault Lab** (admin). Choose a scenario and inject it live.
6. **Eval dashboard.**
   - Pareto chart
   - per-category accuracy
   - calibration diagram
   - run comparison
   - Langfuse links
7. **Audit explorer.** Provenance chain per change, plus a chain-verification badge.

**Accessibility:** keyboard navigation, visible focus, reduced-motion support, and WCAG AA contrast.

## 9. Testing

| Level | Scope |
|---|---|
| Unit | pytest/vitest throughout, written test-first |
| Policy | `opa test`: at least one allow and one deny case per tier and per denied class |
| Auth negative | wrong `aud`; expired token; missing or forged `act`; scope escalation; replayed `jti`; T2 without fresh ACR; self-approval |
| Contract | MCP tool schemas; OpenAPI drift check |
| Parity | the same tool call gives equivalent results in live and replay mode on captured scenarios |
| Integration | testcontainers with Postgres and Keycloak; full token-exchange flow; queue lease and resume |
| End-to-end | Playwright on kind in GitHub Actions: inject → incident → root cause → T0 auto-merge → ArgoCD sync → recovery verified by a health probe |
| Eval gate | replay smoke set (§6.9) |
| Infra | `terraform validate`, tflint, Checkov/Trivy config scans, kubeconform on rendered manifests |

## 10. Infrastructure, CI/CD and cost

### 10.1 Environments

- **Local.** `make up` creates a k3d cluster, installs ArgoCD and registers the app-of-apps against the repo. ArgoCD deploys everything else. Estimated footprint is 8–9 GB RAM.
- **GKE.** Terraform modules:
  - `network`: VPC, subnet, firewall
  - `gke`: zonal Standard cluster, spot node pool
  - `storage`: GCS buckets for snapshots, backups and Terraform state
  - `secrets`: Secret Manager
  - `iam`: Workload Identity, and Workload Identity Federation for GitHub Actions with no service-account keys
  - `budget`: billing alerts at $10, $25 and $50
  - `bootstrap`: ArgoCD via the Helm provider

  Remote state lives in a versioned GCS bucket.
- **ArgoCD:**
  - app-of-apps with sync waves: CRDs → operators → platform → workload → seed
  - overlays: `local/` and `gke/`
  - a demo-seed job that loads pre-captured snapshots and eval results
- **Interview runbook:** `terraform apply` → wait for ArgoCD healthy → smoke test → live Fault Lab demo → `terraform destroy` → billing check.

### 10.2 CI/CD (GitHub Actions)

- **On every PR:**
  - lint and type checks (ruff, mypy, eslint, tsc)
  - unit tests and `opa test`
  - Terraform checks; manifest render plus kubeconform
  - image build plus Trivy scan
  - the eval gate, when its paths change
  - end-to-end tests on kind, for PRs labelled `e2e` and on merge
- **On merge to `main`:**
  1. Build images.
  2. Generate SBOMs.
  3. Sign with cosign keyless.
  4. Push to GHCR.
  5. Commit the image-tag bump under `deploy/`.
  6. ArgoCD syncs.

### 10.3 Budget ($100 total)

| Item | USD | Enforcement |
|---|---|---|
| LLM: development and prompt iteration | 25 | LiteLLM key `dev` |
| LLM: full benchmark sweeps (test split × 4 configs, ~2 sweeps) | 30 | LiteLLM key `eval` |
| LLM: CI smoke evals | 10 | LiteLLM key `ci` |
| GKE: test runs and interviews | 15 | GCP budget alerts; destroy after use |
| Buffer | 20 | — |

**Free services:** Langfuse Cloud free tier, Keycloak, GitHub, GHCR, Hugging Face, `sslip.io` hostnames.

## 11. Project wiki

- **Location:** `wiki/`, versioned with the code. Pages:
  - `index.md`: map of the wiki
  - `status.md`: current milestone and next steps
  - `architecture.md`
  - `adr/NNNN-*.md`: one per decision in §2, plus new ones as they arise
  - `components/<name>.md`
  - `runbooks/` (local up, GKE spin-up, teardown, capture batch)
  - `security/threat-model.md`
  - `eval/results.md`
  - `glossary.md`
  - `log.md`: dated, append-only
- **Enforcement:** the project skill `.claude/skills/rootline-wiki/SKILL.md`, with pointers in `AGENTS.md` and `CLAUDE.md`. It requires every agent to:
  1. read `wiki/index.md` and `wiki/status.md` before starting work
  2. update the affected component and runbook pages, and add an ADR for any new decision, after finishing
  3. append a dated entry to `wiki/log.md`
- **Setup:** the wiki and skill are the first deliverable of week 1.

## 12. Planning-time decisions

These are resolved during implementation planning, not left open during the build. Each has a clear decision rule.

| Item | Decision rule |
|---|---|
| Exact small and large model IDs | Lowest cost meeting tool-use and structured-output reliability on a 10-scenario pilot; prices checked against current provider pricing |
| Ollama baseline model | Best tool-calling open-weight model that runs on CPU on the 16 GB laptop |
| Public benchmark (ITBench vs Cloud-OpsBench) | Permissive licence, < 1 day adapter effort, mappable to the semantic tool layer |
| Keycloak federated SA auth vs `private_key_jwt` | Federated if it works on the pinned Keycloak version with projected tokens; otherwise the fallback |
| GKE node shape and count | Smallest spot shape that fits the measured k3d footprint plus GKE system overhead |
| Trimmed OTel Demo service set | Keep every service targeted by a fault type in §6.1; drop the rest |

## 13. Milestones (8 weeks)

| Week | Deliverables |
|---|---|
| 1 | Wiki and skill; repo layout; k3d + ArgoCD bootstrap; trimmed OTel Demo and telemetry; CI skeleton |
| 2 | Fault Lab (all three channels); snapshot capture; labels; overnight capture running |
| 3 | MCP servers (live and replay); Keycloak; workload identity; token exchange |
| 4 | **End-to-end minimal version:** agent v1, LiteLLM, Langfuse, non-LLM baseline, first eval numbers |
| 5 | Verifier; preprocessing; memory; fix catalogue; OPA tiers; GitHub App PR flow |
| 6 | Console (live investigation, approvals with step-up, eval dashboard, audit explorer) |
| 7 | Terraform GKE and runbook; cosign and Kyverno; full sweeps; public-benchmark subset |
| 8 | Hardening; threat model; Hugging Face publication; write-up; demo video; buffer |

**Cut order if behind schedule:** public-benchmark subset → incident memory → console polish. The week-4 end-to-end version is never cut.

**Version 2 stretch:** distil a small open-weight model (LoRA on free Kaggle/Colab GPUs), trained on dev-split investigations with large-model diagnoses as labels, then benchmark it on cost vs accuracy.

## 14. Risks

| Risk | Mitigation |
|---|---|
| RAM pressure on the 16 GB laptop | Trim the OTel Demo; single-binary Loki/Tempo; measure in week 1 and adjust |
| Agent accuracy low on hard categories | Report honestly with CIs; inconclusive is a valid outcome; analyse failure taxonomy in the write-up |
| LLM spend overrun | Per-key LiteLLM hard budgets; replay instead of live runs; CI eval gate runs only on path changes, with 10 scenarios by default |
| Live and replay drift | Parity tests; snapshots versioned with tool-layer version |
| Keycloak token-exchange edge cases | Integration tests in week 3; fallback in §5.2 |
| GKE leftover resources billing | Budget alerts; `terraform destroy` in the runbook; post-destroy billing check |
| Scope creep | Cut order (§13); YAGNI; wiki `status.md` reviewed weekly |
