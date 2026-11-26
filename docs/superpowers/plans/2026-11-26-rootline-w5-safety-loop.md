# Rootline Implementation Plan — Week 5: Safety Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The agent proposes typed fixes through `mcp-gitops.propose_fix`; the gate classifies each proposal with OPA (T0/T1/T2/DENIED), auto-merges T0, waits for passkey-backed approvals for T1/T2, merges, syncs ArgoCD and verifies recovery; approvals and every state change are audited and verifiable; incident memory is written on verified fixes; capture reaches 300 scenarios.

**Architecture:** Rendering of an action into file changes lives in one function shared by `mcp-gitops` (to open the PR) and `gate` (to re-render and compare tree hashes). `api` owns proposal state and validates every transition against POL-010; `gate` drives the lifecycle through `api` internal endpoints and talks to GitHub and ArgoCD. OPA runs as a localhost sidecar with the policy bundle baked into the gate image.

**Tech Stack:** OPA 1.x (Rego v1), GitHub REST (pulls, check runs, git data), ArgoCD REST, ruamel.yaml, fastembed, pgvector.

## Global Constraints

All constraints in `2026-11-26-rootline-00-overview.md` → "Global Constraints" apply. Week-specific additions:

- Default-deny: any OPA error, timeout (2 s) or missing field results in tier `DENIED` with reason `policy_error` (SEC-001).
- The agent App is never a ruleset bypass actor (T6); only the gate merges.
- Week 5 acceptance (MS-001): TST-POL-*, TST-API-001, TST-SEC-035 pass; manual demo of a T0 auto-merge and a T1 approval (via the API) verified on local; capture complete (300, S3).

---

### Task W5-T01: OPA policy `rootline.fix` and tests

**Requirement IDs:** POL-030, POL-031, POL-032, POL-040, POL-041, TST-POL-001….
**Depends on:** W4 complete. **Branch:** `feat/w5-policy`.

**Files:** `policies/opa/rootline/fix.rego`, `policies/opa/rootline/fix_test.rego`, `policies/opa/rootline/testdata/base_input.json`.

**Input additions (recorded in ADR 0030 and spec §26):** `approvals[].step_up_ok: bool` (computed by `api` per `security.stepUpMode`, so the policy works in both SEC-022 and SEC-023 modes); `argocd.out_of_sync[].workload: str` (the `rootline-env` component file containing the object; `flagd-config` for the flag ConfigMap); `change.files[].workload` may be `null` for files that are not `workload/<component>.yaml`; `config.agent_bot_login`, `config.gate_bot_login`.

- [ ] **Step 1: Write `fix.rego`**

```rego
package rootline.fix

import rego.v1

denied_kinds := {"Secret", "Role", "RoleBinding", "ClusterRole", "ClusterRoleBinding", "ServiceAccount",
	"Namespace", "CustomResourceDefinition", "ResourceQuota", "LimitRange"}

git_types := {"revert_commit", "scale", "set_resources", "restart"}

t0_types := {"revert_commit", "resync_app", "restart"}

action := input.proposal.action

git_change if action.type in git_types

# ---------- 1. DENIED ----------
deny_reasons contains "scale_to_zero" if {
	action.type == "scale"
	action.replicas == 0
}

deny_reasons contains "file_outside_workload" if {
	some f in input.change.files
	not startswith(f.path, "workload/")
}

deny_reasons contains sprintf("forbidden_kind:%s", [k]) if {
	some f in input.change.files
	some k in f.kinds
	k in denied_kinds
}

deny_reasons contains sprintf("foreign_namespace:%s", [ns]) if {
	some f in input.change.files
	some ns in f.namespaces
	ns != "shop"
}

deny_reasons contains "unexpected_pr_author" if {
	git_change
	input.change.pr_author != input.config.agent_bot_login
}

deny_reasons contains "diff_mismatch" if {
	git_change
	input.change.rendered_tree_sha != input.change.pr_tree_sha
}

deny_reasons contains "revert_target_too_old" if {
	action.type == "revert_commit"
	input.commit.age_seconds > 86400
}

deny_reasons contains "revert_target_not_on_main" if {
	action.type == "revert_commit"
	not input.commit.on_main
}

deny_reasons contains "revert_target_is_merge" if {
	action.type == "revert_commit"
	input.commit.is_merge
}

deny_reasons contains "revert_of_gate_commit" if {
	action.type == "revert_commit"
	input.commit.author == input.config.gate_bot_login
}

deny_reasons contains "investigation_not_diagnosed" if input.investigation.status != "diagnosed"

deny_reasons contains "verification_failed" if not input.investigation.verification_passed

# ---------- 2. T2 ----------
t2_reasons contains "touches_statefulset" if {
	some f in input.change.files
	"StatefulSet" in f.kinds
}

t2_reasons contains "touches_networkpolicy" if {
	some f in input.change.files
	"NetworkPolicy" in f.kinds
}

t2_reasons contains sprintf("stateful_workload:%s", [f.workload]) if {
	some f in input.change.files
	f.workload in input.config.stateful_workloads
}

t2_reasons contains sprintf("stateful_target:%s", [action.workload]) if {
	action.type in {"scale", "set_resources", "restart"}
	input.workloads[action.workload].stateful
}

# ---------- 3. T0 conditions (a failure explains why the tier is not T0) ----------
t0_failures contains "action_type_not_t0" if not action.type in t0_types

t0_failures contains "commit_older_than_30m" if {
	action.type == "revert_commit"
	input.commit.age_seconds > 1800
}

t0_failures contains "commit_touches_multiple_workloads" if {
	action.type == "revert_commit"
	count({f.workload | some f in input.change.files; f.workload != null}) != 1
}

t0_failures contains "commit_touches_non_workload_file" if {
	action.type == "revert_commit"
	some f in input.change.files
	f.workload == null
}

t0_failures contains "resync_scope_too_wide" if {
	action.type == "resync_app"
	ws := {r.workload | some r in input.argocd.out_of_sync; r.workload != "flagd-config"}
	count(ws) > 1
}

t0_failures contains "resync_touches_stateful" if {
	action.type == "resync_app"
	some r in input.argocd.out_of_sync
	r.workload != "flagd-config"
	r.workload in input.config.stateful_workloads
}

t0_failures contains "restart_stateful" if {
	action.type == "restart"
	input.workloads[action.workload].stateful
}

t0_failures contains "confidence_below_threshold" if {
	input.investigation.confidence < input.config.t0_confidence_threshold
}

t0_failures contains "suspected_injection" if input.investigation.suspected_injection

t0_failures contains "t0_circuit_breaker" if input.recent_t0_merges >= input.config.max_t0_per_hour

t0_failures contains "prior_ineffective_fix" if input.incident.prior_ineffective

# ---------- tier ----------
tier := "DENIED" if count(deny_reasons) > 0

tier := "T2" if {
	count(deny_reasons) == 0
	count(t2_reasons) > 0
}

tier := "T0" if {
	count(deny_reasons) == 0
	count(t2_reasons) == 0
	count(t0_failures) == 0
}

tier := "T1" if {
	count(deny_reasons) == 0
	count(t2_reasons) == 0
	count(t0_failures) > 0
}

requirements := {"approvals": 0, "step_up": false, "distinct_from_initiator": false, "comment_min_len": 0} if {
	tier in {"T0", "DENIED"}
}

requirements := {"approvals": 1, "step_up": true, "distinct_from_initiator": false, "comment_min_len": 0} if {
	tier == "T1"
}

requirements := {"approvals": 1, "step_up": true, "distinct_from_initiator": true, "comment_min_len": 20} if {
	tier == "T2"
}

valid_approval(a) if {
	"approver" in a.roles
	a.step_up_ok == true
	not requirements.distinct_from_initiator
	count(a.comment) >= requirements.comment_min_len
}

valid_approval(a) if {
	"approver" in a.roles
	a.step_up_ok == true
	requirements.distinct_from_initiator
	a.approver_sub != input.investigation.on_behalf_of
	count(a.comment) >= requirements.comment_min_len
}

default satisfied := false

satisfied if tier == "T0"

satisfied if {
	tier in {"T1", "T2"}
	some a in input.approvals
	valid_approval(a)
}

reasons := sort(array.concat([r | some r in t2_reasons], [r | some r in t0_failures])) if {
	tier != "T0"
}

reasons := ["all_t0_conditions_met"] if tier == "T0"

decision := {
	"tier": tier,
	"allow": tier != "DENIED" and satisfied,
	"reasons": reasons,
	"deny_reasons": sort([r | some r in deny_reasons]),
	"requirements": requirements,
	"satisfied": satisfied,
}
```

The input builder always sets `approvals[].comment` to a string (`""` when absent) so `count()` is defined. `input.investigation.on_behalf_of` is `null` in system mode, so `a.approver_sub != null` is true and the T2 distinct rule is trivially satisfied (POL-060 step 4). Run `opa check policies/opa` and `opa fmt -w policies/opa`; replace any construct that `opa check --v1-compatible` rejects (for example the `and` in `decision.allow` — rewrite as a helper rule `allow if { tier != "DENIED"; satisfied }` with `default allow := false` if needed).

- [ ] **Step 2: Write `fix_test.rego` (TST-POL-001 …)** — `testdata/base_input.json` is a T0-eligible `revert_commit`: diagnosed, verified, confidence 0.9, no injection, 1 file `workload/payment.yaml` (workload `payment`, kinds `["Deployment"]`, namespaces `["shop"]`), tree SHAs equal, author = agent bot, commit age 600 s on main not merge, 0 recent merges, no approvals, config per POL-040 with `stateful_workloads: ["valkey-cart", "kafka", "astronomy-db"]`. Each test overrides one field with `object.union` / `json.patch`. Required tests (one allow and one deny case per rule; names prefixed `test_tst_pol_001_…`):

| Test pair | Override | Expect |
|---|---|---|
| scale_to_zero | `action = {type: scale, workload: payment, replicas: 0}` vs replicas 2 | DENIED `scale_to_zero` vs not that reason |
| file_outside_workload | file path `.rootline/baseline.json` | DENIED |
| forbidden_kind | kinds `["Secret"]` (and each other denied kind, looped with a comprehension) | DENIED `forbidden_kind:Secret` |
| foreign_namespace | namespaces `["rootline"]` | DENIED |
| unexpected_pr_author | `pr_author: "someone"` | DENIED; resync_app with any author → not denied |
| diff_mismatch | `pr_tree_sha` differs | DENIED |
| revert_target_too_old / not_on_main / is_merge / gate commit | each field | DENIED with that reason |
| not diagnosed / verification failed | each | DENIED |
| touches_statefulset / networkpolicy / stateful_workload / stateful_target | each | T2 |
| T0 happy path | base | `tier T0`, `allow true`, `reasons ["all_t0_conditions_met"]` |
| commit_older_than_30m | age 1801 | T1 |
| commit_touches_multiple_workloads | two files, two workloads | T1 |
| resync_scope | out_of_sync `flagd-config` + `payment` → T0; + `cart` → T1; + `valkey-cart` → T1 |
| restart_stateful | restart `valkey-cart` | T2 (stateful_target) |
| confidence | 0.79 → T1; 0.80 → T0 |
| suspected_injection | true → T1 |
| circuit_breaker | `recent_t0_merges: 3` → T1; 2 → T0 |
| prior_ineffective | true → T1 |
| scale non-zero | `scale payment 2` → T1 (not a T0 type) |
| T1 approval | one approval `{roles:[approver], step_up_ok:true, comment:""}` → `satisfied`, `allow` |
| T1 without step-up | `step_up_ok:false` → not satisfied |
| T1 viewer approval | roles `[viewer]` → not satisfied |
| T2 self-approval | delegated, `on_behalf_of: "u1"`, approver `u1` → not satisfied; approver `u2` with 20-char comment → satisfied; 19 chars → not |
| T2 system mode | `on_behalf_of: null`, approver `u1`, 20 chars → satisfied |
| DENIED never allowed | DENIED with a valid approval → `allow false` |
| requirements shape | each tier returns the POL-032 requirements object |

Run: `opa test policies/opa -v` → all PASS; `opa test policies/opa --coverage --format json | jq .coverage` ≥ 95.
- [ ] **Step 3: Commit** `feat(policies): add rootline.fix OPA policy with tests`.

---

### Task W5-T02: Shared action rendering, OPA input builder, replay policy evaluation

**Requirement IDs:** MCP-040 step 2, POL-030 (diff_mismatch), POL-040, EVL-020 (policy in replay), EVL-030 (`unsafe_proposal_rate`, `policy_catch_rate`).
**Depends on:** W5-T01, W2-T07. **Branch:** `feat/w5-render-and-input`.

**Files:**
- Create: `libs/py-common/rootline_common/gitops_render.py`
- Create: `services/gate/rootline_gate/{opa_input,opa_client}.py`
- Modify: `eval/runner/rootline_eval/scoring.py` (policy evaluation via `opa eval`)
- Test: `libs/py-common/tests/test_gitops_render.py`, `services/gate/tests/test_opa_input.py` (hypothesis property tests), `eval/runner/tests/test_scoring_policy.py`

**Interfaces:**
- `gitops_render.render_action(repo: EnvRepo, action: ActionSpec, *, base_ref: str = "main", now: datetime) -> RenderResult(files: dict[str, str | None], summary: str, workload: str | None)` — `revert_commit` → `repo.revert_tree(sha)` (raises `RevertConflict` → caller returns `invalid_argument "revert conflicts"`); `scale` → `spec.replicas = n`; `set_resources` → the container's `resources.{requests,limits}.{memory,cpu}` fields that are set; `restart` → pod-template annotation `rootline.dev/restarted-at: <to_rfc3339(now)>`; all YAML edits through `ruamel.yaml` round-trip (`YAML(typ="rt")`, `preserve_quotes=True`, width 4096) on `workload/<workload>.yaml`, editing only the document whose `kind ∈ {Deployment, StatefulSet}` and `metadata.name == workload`; `resync_app`/`none` → `files = {}`. `summary` e.g. `revert_commit 3f2a9c1`, `scale quote 2`, `set_resources cart/cart memory_limit=512Mi`, `restart payment`.
- `rootline_gate.opa_input.build_input(ctx: ProposalContext, pr: PrInfo | None, commit: CommitInfo | None, argocd_app: dict, workloads: dict[str, WorkloadInfo], recent_t0_merges: int, config: PolicyConfig) -> dict` — exact POL-040 shape plus the W5-T01 additions; `change.files` built from the PR's file list: for each path, parse old and new content (`yamlio.load_docs`), take documents that differ, `kinds` = sorted set of their kinds, `namespaces` = sorted set of their `metadata.namespace` (missing → `"shop"` only if the file is under `workload/`, else `"_unknown_"`), `workload` = `<component>` from `workload/<component>.yaml` else `null`.
- `rootline_gate.opa_client.evaluate(input: dict, url="http://127.0.0.1:8181/v1/data/rootline/fix/decision", timeout=2.0) -> dict` → on any error returns `{"tier": "DENIED", "allow": False, "reasons": [], "deny_reasons": ["policy_error"], "requirements": {...T0/DENIED shape}, "satisfied": False}`.
- `rootline_eval.scoring.policy_tier(action, label, run, report, snapshot) -> str` — builds a replay input (stub context: diagnosed/verification from the result; PR author = agent bot; tree SHAs equal; commit info from `git/commits.json`; out-of-sync from `argocd/app.json`; workloads from `k8s/objects.json`; `recent_t0_merges = 0`; no approvals) and runs `opa eval --data policies/opa --input <tmp> --format json data.rootline.fix.decision`.

- [ ] **Step 1: Tests** — render: each action type against the fixture workload files produces exactly the expected YAML diff (golden files) and preserves all other bytes (compare line-by-line outside the edited lines); `restart` annotation timestamp from the injected `now`. Input builder (hypothesis): for arbitrary combinations of file paths/kinds/namespaces the produced input always validates against a JSON schema of POL-040 (`services/gate/tests/opa_input.schema.json`), `files[].workload` is `null` exactly for non-`workload/` paths, and the output is deterministic (sorted lists). OPA client: connection refused → DENIED `policy_error`. Scoring: `unsafe_proposal` true when the replay tier is DENIED; `policy_catch_rate` counts unsafe proposals whose tier is DENIED, T1 or T2.
- [ ] **Step 2: Implement; commit** `feat(gate): add shared action rendering, OPA input builder and replay policy scoring`.

---

### Task W5-T03: `propose_fix` and agent wiring

**Requirement IDs:** MCP-040, MCP-041, AGT-026, AGT-082, §8.4, SEC-131 (`proposal.created`).
**Depends on:** W5-T02, W5-T04 (internal endpoint; develop both on one branch or merge W5-T04 first). **Branch:** `feat/w5-propose-fix`.

**Files:** `services/mcp-gitops/rootline_mcp_gitops/{propose,inventory}.py`, modify `tools.py`, `app.py`; `services/agent/rootline_agent/nodes/plan_fix.py`; tests `services/mcp-gitops/tests/test_propose.py`, `services/agent/tests/test_plan_fix.py`.

**Behaviour (MCP-040, exact order):**
1. **Validate** against the live inventory (`inventory.load()` reads `workload/*.yaml` at `main` via `EnvRepo` and the last 24 h of commits): workload exists; container exists for `set_resources`; `revert_commit.sha` resolves (prefix ≥ 7) to a commit on `main` within 24 h; `set_resources` new values within 0.25×–4× of the current value of the same field (fields absent in the current spec: bounds only); request ≤ limit after applying the change to the current spec. Failure → `ToolError("invalid_argument", <reason>)`.
2. **Idempotency (MCP-041):** `action_hash(action)`; `GET /internal/v1/proposals?investigation_id=&action_hash=` on `api` → if found, return it unchanged.
3. **Render** with `render_action`.
4. For Git-changing actions: branch `rootline/fix/<incident_id[-8:]>-<proposal_id[-8:]>` (proposal ID generated here with `new_ulid()`), `commit_files(..., branch=<new branch>, parent=<main head>)` after creating the ref (`POST /git/refs`), author/committer `CommitAuthor("<agent bot login>", "<app id>+<agent bot login>@users.noreply.github.com")`, message `fix(<workload or "workload">): <summary> [incident <incident_id>]`; PR `POST /repos/arkhash0309/rootline-env/pulls` (title = message, head = branch, base = main, body = rationale + `Report: https://console.<D>/investigations/<investigation_id>` + action JSON in a ```json block); label `rootline-fix` (`POST /issues/<n>/labels`).
5. **Register** `POST /internal/v1/proposals` with `{id, investigation_id, incident_id, report_id, action, action_hash, rationale, pr_number, pr_url, branch, diff_text (PR diff ≤ 300 lines), rendered_tree_sha (tree of the fix commit), requested_by = principal sub, acting_agent = principal act_client_id (or azp in azp mode), principal_mode}` → `{proposal_id, status: "pending_policy"}`.
6. Return `{proposal_id, status, pr_number?, pr_url?, dry_run: false}`.
Replay/eval mode (`ROOTLINE_MCP_MODE=replay`): validate against the snapshot inventory (`k8s/objects.json`, `git/commits.json`), skip 2–5, return `{proposal_id: <ULID>, status: "pending_policy", dry_run: true}`; the eval runner records the action from the tool call arguments.

`get_proposal_status` now calls `GET /internal/v1/proposals/{id}` (mcp-gitops is in the `azp` allowlist for that read) and returns `{proposal_id, status, tier?, reasons, pr_number?}`. Add `mcp-gitops` to the allowlist of `GET /internal/v1/proposals` and `GET /internal/v1/proposals/{id}` in W5-T04 (recorded in spec §26).

Agent `plan_fix` (AGT-026): after `FixPlan`, call `propose_fix` with `{incident_id, investigation_id, report_id, action, rationale}` (report ID from `recorder.report(...)`, which therefore runs before `propose_fix`; move the report call from `finalize` to the end of `verify` when it passes); on `invalid_argument` append the error message to the conversation and retry `plan_fix` once; second failure → `proposal_error = <message>`, status stays `diagnosed`, no proposal; on success emit `proposal.updated {proposal_id, status}`.

- [ ] **Step 1: Tests (respx GitHub + fake api)** — validation failures (unknown workload; sha older than 24 h; memory 5× current; cpu below 50m); idempotent second call makes no GitHub calls; branch name, commit message and PR body exact; replay mode makes no network calls and returns `dry_run: true`; agent retry path with a scripted `invalid_argument` then success; second failure ends `diagnosed` with `proposal_error`.
- [ ] **Step 2: Implement; commit** `feat(mcp-gitops): add propose_fix with validation, PR creation and registration`.

---

### Task W5-T04: `api` proposals, approvals and incident lifecycle

**Requirement IDs:** POL-010, POL-031 (stats), POL-060, POL-070 (re-investigation), API-050 (proposal rows), API-062 (proposal states), §12.3 (proposals endpoints), SEC-023a, SEC-131, TST-POL-020, TST-POL-030.
**Depends on:** W4-T07. **Branch:** `feat/w5-api-proposals`.

**Files:** `services/api/rootline_api/routers/{proposals,internal_gate}.py`, `services/api/rootline_api/services/{proposals,approvals}.py`; tests `test_proposal_transitions.py`, `test_approvals.py`, `test_incident_status.py`.

**Behaviour:**
- `TRANSITIONS: dict[str, set[str]]` exactly the POL-010 table (`pending_policy → {denied, approved, awaiting_approval, recorded}`, `awaiting_approval → {approved, rejected, expired}`, `approved → {merged, failed}`, `merged → {synced, failed}`, `synced → {verified, ineffective}`); actor rules: `rejected` only via the public reject endpoint; all others only via `POST /internal/v1/proposals/{id}/transition` from `rootline-gate`. Invalid → 409 `invalid_transition` with detail `"<from> -> <to>"`. Each transition sets `merged_at`/`synced_at`/`verified_at` where relevant, stores `tier`/`policy_decision`/`merge_commit_sha`/`error`, emits SSE event `proposal.updated` on the investigation, writes the audit action (`proposal.policy_evaluated` on the first transition out of `pending_policy` with payload `{tier, reasons, deny_reasons}`, then `proposal.approved` (T0 auto, actor `rootline-gate`), `proposal.denied`, `proposal.merged`, `proposal.synced`, `proposal.verified`, `proposal.ineffective`, `proposal.failed`, `proposal.rejected`), and recomputes the incident status per API-062.
- `POST /internal/v1/proposals` (mcp-gitops) → inserts with status `pending_policy`, audit `proposal.created` (actor = `requested_by`, `on_behalf_of` = investigation's `on_behalf_of`); duplicate `(investigation_id, action_hash)` → returns the existing row (200).
- `GET /internal/v1/proposals?status=&investigation_id=&action_hash=` (gate, mcp-gitops); `GET /internal/v1/proposals/{id}` (gate, mcp-gitops); `GET /internal/v1/proposals/stats?window=60m&tier=T0&status=merged,synced,verified,ineffective` → `{"count": n}` over `merged_at ≥ now − window`; `GET /internal/v1/proposals/{id}/context` → `{proposal, investigation {id, status, principal_mode, on_behalf_of, suspected_injection, verification_passed, confidence}, incident {id, prior_ineffective}, approvals [{approver_sub, roles, acr, auth_time, comment, step_up_ok}]}`; `GET /internal/v1/incidents/{id}/alerts?state=firing`.
- **Approve (POL-060):** checks in order 1–6; errors: not awaiting → 409 `invalid_transition`; role → 403 `forbidden`; step-up (`acr == "step-up"`, or with `step_up_mode == "auth_time"`: `now − auth_time ≤ 300`) → 401 `insufficient_user_authentication` with the SEC-023a header; T2 self-approval → 403 `separation_of_duties`; T2 comment < 20 → 422 `validation_error`; idempotency per API-007. On success: insert `core.approvals` (`decision approve`, `acr`, `auth_time`, `idempotency_key`), audit `proposal.approved` (actor = caller sub, payload `{acr, auth_time, tier}`), then `POST {gate_url}/internal/v1/proposals/{id}/reevaluate` with the `rootline-api` service-account token (audience `rootline-gate`); a gate call failure is logged and the approval stands (the gate's 5 s loop also re-evaluates). Returns `ProposalDetail`.
- **Reject:** approver (no step-up required), comment 1–1000; transition `awaiting_approval → rejected`; audit; the gate closes the PR on its next loop (it sees status `rejected`).
- **Step-up audit (§14.2):** `GET /v1/me` with a token whose `acr == "step-up"` and whose `jti` was not seen before writes `auth.step_up_succeeded` (dedupe by `jti` in a small table `core.seen_step_up_jti(jti text primary key, ts)` added by migration `0004_seen_jti` (overview §4)).
- **Incident status (API-062):** `recompute(incident_id)` derives the status from the latest investigation and active proposal in this precedence: `closed` (manual) > `fix_ineffective` (latest proposal ineffective and no newer investigation running) > `resolved` (a proposal verified, or all alerts resolved ≥ 5 min and no active proposal — the 5-min rule is evaluated by a background task that runs every 60 s) > `fix_applied` (merged/synced) > `fix_proposed` (pending_policy/awaiting_approval/approved) > `investigating` (running) > `inconclusive` / `diagnosed` (latest investigation outcome) > `open`.
- **Ineffective (POL-070):** on transition to `ineffective`, if the incident has no previous re-investigation (`payload.prior_ineffective` false for all its jobs), enqueue a new investigation with the original `principal_mode` (system: as API-061; delegated: system mode with `on_behalf_of` kept, because no fresh user token is available — record in spec §26) and `prior_ineffective = true`.

- [ ] **Step 1: TST-POL-020** — every allowed transition succeeds and writes exactly one audit row; every disallowed pair (all `from × to` not in the table, generated) returns 409; a non-gate `azp` on the transition endpoint → 403.
- [ ] **Step 2: TST-POL-030** — approve as viewer (403), approver without step-up (401 + header text exact), approver with step-up on T1 (200), T2 self-approval in delegated mode (403 `separation_of_duties`), T2 short comment (422), T2 system mode by owner (200), repeated `Idempotency-Key` (same response), same key different body (409 `conflict`), proposal not awaiting (409), `auth_time` mode honoured when `step_up_mode=auth_time`.
- [ ] **Step 3: Incident status tests** for each API-062 row, including re-investigation once on ineffective and never twice.
- [ ] **Step 4: Implement; regenerate OpenAPI; commit** `feat(api): add proposal lifecycle, approvals and incident status`.

---

### Task W5-T05: `gate` service

**Requirement IDs:** POL-001, POL-050, POL-051, POL-052, POL-070, POL-080, OBS-002 (`rootline_proposals_total`, `rootline_gate_stage_duration_seconds`), TST-POL-020 (gate side).
**Depends on:** W5-T02, W5-T04. **Branch:** `feat/w5-gate`.

**Files:** `services/gate/rootline_gate/{app,loop,tasks,github_ops,argocd_ops,settings,main}.py`; tests `services/gate/tests/{test_tasks,test_checks,test_classify,test_reevaluate}.py`.

**Behaviour:**
- `loop.Loop` runs the POL-050 periodic tasks as independent asyncio tasks (each wrapped so an exception is logged and the task continues next interval).
- `evaluate_pending` (5 s): for each `pending_policy` (and for `awaiting_approval` proposals flagged by `reevaluate` or every 30 s): fetch context (`/context`), PR (`GET /pulls/{n}`, `/pulls/{n}/files`, contents at base and head), commit info for `revert_commit` (`GET /commits/{sha}`: author login, `committed_at` → `age_seconds = now − committed_at`, `on_main` via `GET /compare/{sha}...main` status `ahead|identical`, `is_merge = len(parents) > 1`), ArgoCD app (`out_of_sync` with workload mapping from `workload/*.yaml` object names), workloads (kind and `stateful = kind == "StatefulSet" or name in stateful_workloads`), `recent_t0_merges` (stats endpoint), recompute `rendered_tree_sha` by calling `render_action` on the PR base and creating a tree via `POST /git/trees` with `base_tree` = base commit tree (no commit, no ref), and compare with the PR head commit's tree (`pr_tree_sha`). Evaluate OPA. Transition: action `none` → `recorded` (no OPA call; check run not created because there is no PR); DENIED → `denied`, close the PR with a comment listing `deny_reasons`, check `failure`; T0 → `approved`; T1/T2 without satisfying approvals → `awaiting_approval`, check `in_progress` with summary `Awaiting approval (T1)` / `(T2)` and console link; T1/T2 satisfied → `approved`.
- `process_approved` (5 s): Git actions → `PUT /pulls/{n}/merge {"merge_method": "squash", "commit_title": <PR title>}` → transition `merged` with `merge_commit_sha`, check `success`; conflict (405/409) or 3 failed retries → `failed`; `resync_app` → `argocd.sync(prune=False)` → `merged` (merge_commit_sha = null).
- `watch_sync` (10 s): `merged` → ArgoCD `Synced` with `sync.revision` == merge commit (or any revision for resync, after the sync request time) and `Healthy` → `synced`; older than 10 min → `failed` with error `sync_timeout`.
- `watch_verify` (15 s): `synced` → incident alerts endpoint; maintain per-proposal `clear_since`; empty continuously for 120 s starting ≤ 10 min after `synced_at` → `verified`; otherwise at `synced_at + 10 min` with no qualifying clear period → `ineffective`.
- `expire` (60 s): `awaiting_approval` with `updated_at < now − 60 min` → `expired`, close PR, check `failure`.
- `classify_prs` (15 s, POL-080): for every open PR on `rootline-env`: author = agent bot and label `rootline-fix` → if no proposal references the PR number within 2 min of `created_at` → check `failure` "orphan fix PR"; author = owner login (`OWNER_GITHUB_LOGIN=arkhash0309`) → check `success` "human change (owner)"; anyone else → check `failure` "unrecognised author". Checks are created once per head SHA (idempotent: list existing check runs for the SHA by name).
- Check runs (POL-051): `POST /check-runs {name: "rootline-gate/policy", head_sha, status, conclusion?, output: {title, summary}}`; updates via `PATCH /check-runs/{id}`; summary lists `reasons` and `deny_reasons` as bullet lists.
- `POST /internal/v1/proposals/{id}/reevaluate` (POL-052): validates bearer with audience `rootline-gate`, `azp == "rootline-api"`, scope `api:internal`; marks the proposal for immediate evaluation; 202.
- Metrics: `rootline_proposals_total{tier, final_status}` incremented on terminal transitions; `rootline_gate_stage_duration_seconds{stage}` observed for policy (pending→decision), approval (awaiting→approved), merge, sync, verify.

- [ ] **Step 1: Tests with fakes** (fake api client, respx GitHub, fake ArgoCD, fake OPA): T0 revert proposal goes `pending_policy → approved → merged → synced → verified` across task ticks with a fake clock; DENIED closes PR and fails check; T1 waits, then `reevaluate` with an approval → approved; merge conflict → `failed`; sync timeout → `failed`; alerts re-fire within the clear period → clear timer resets; 10 min without 2 min clear → `ineffective`; expiry at 60 min; PR classification three cases + orphan timing; OPA down → DENIED `policy_error`; reevaluate endpoint auth (wrong azp → 403).
- [ ] **Step 2: Implement; commit** `feat(gate): add policy gate loop with merge, sync and recovery verification`.

---

### Task W5-T06: Incident memory

**Requirement IDs:** AGT-090, AGT-091, AGT-092, AGT-093, DB (migration 0005).
**Depends on:** W5-T04. **Branch:** `feat/w5-memory`.

- [ ] **Step 1: Migration `0005_memory_vector`** — `CREATE EXTENSION IF NOT EXISTS vector;` then `core.incident_memory` and its HNSW index verbatim (§13.4); grants to `rootline_api`. (`CREATE EXTENSION` needs superuser: CNPG `postInitApplicationSQL` creates the extension at cluster init in `rootline`; add `postInitApplicationSQL: ["CREATE EXTENSION IF NOT EXISTS vector"]` to the Postgres chart; the migration's `IF NOT EXISTS` then succeeds as `rootline_migrator`. The testcontainers fixture runs the same statement as superuser before migrating.)
- [ ] **Step 2: Embedder** — `rootline_common.embed.Embedder` wrapping `fastembed.TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=<ROOTLINE_EMBED_CACHE, default /app/models>)`; `embed(text) -> list[float]` (384, L2-normalised); the api Dockerfile downloads the model at build time into `/app/models` (`RUN /app/.venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/models')"`). Measure api memory after load; if the api pod exceeds its 384 Mi limit, raise its limit to 512 Mi and request to 256 Mi, recompute the S2 total, and record an ADR (ARC-030 deviation).
- [ ] **Step 3: Write path (AGT-091)** — in `api`, on incident status `resolved` with a `verified` proposal and a `diagnosed` investigation: text exactly AGT-090 (`"Root cause: <entity> (<category>). Summary: <summary[:600]>. Fix: <action type> <params as k=v joined by space>. Outcome: verified."`), embedding, `source = "production"`.
- [ ] **Step 4: Read path (AGT-092)** — `POST /internal/v1/memory/search {text}` (azp `rootline-agent`) → top-3 by cosine distance with similarity ≥ 0.75 (`1 - (embedding <=> :q) >= 0.75`), returning `{id, text, similarity}`; the agent's `triage` calls it with query text = trigger text + top 3 anomalies (`"<service> <metric> <direction>"` joined by `; `) and wraps hits per AGT-092. Agent setting `AGENT_MEMORY=on` in-cluster (default on).
- [ ] **Step 5: Eval isolation (AGT-093)** — `rootline_eval.memory.InMemoryStore` with numpy cosine; `--memory on` builds it from the same sweep's `routed` dev results whose `top1_correct and action_acceptable`, text built the same way (`Outcome: verified`); only test-split scenarios query it; with memory off, `triage` gets no hits. Test: with memory off no `memory` data block appears in the triage prompt; with memory on a test scenario gets hits only from dev results.
- [ ] **Step 6: Commit** `feat(agent): add incident memory with pgvector and eval isolation`.

---

### Task W5-T07: Audit verification with approval checks

**Requirement IDs:** SEC-132, TST-SEC-035 (approvals), S5.
**Depends on:** W5-T04. **Branch:** `feat/w5-audit-verify`.

- [ ] **Step 1: Tests** — build an audit log through the real api flows (test client + fake gate): T0 merge without approval → 0 violations; T1 merged with a `proposal.approved` from an approver → 0; T1 `proposal.merged` without a preceding `proposal.approved` → 1 violation `{proposal_id, reason: "missing_approval"}`; T2 approved by the investigation's `on_behalf_of` → violation `self_approval`; approval by a user lacking `approver` at approval time (roles recorded in the approval audit payload) → `approver_role_missing`; tampered row → `chain_ok: false` with `first_bad_id`.
- [ ] **Step 2: Implement** `rootline audit verify [--check-approvals]` and `GET /v1/audit/verify?check_approvals=` (admin; writes `admin.audit_verified` with the result summary); the approval check walks rows in id order per `target = "proposal:<id>"` using the payloads of `proposal.policy_evaluated` (tier), `proposal.approved` (actor, roles), and the investigation `on_behalf_of` recorded in `proposal.created` (`on_behalf_of` column); output `{chain_ok, rows, first_bad_id, approval_violations: [{proposal_id, reason}]}`. Add `roles` to the `proposal.approved` payload in W5-T04 if not already present.
- [ ] **Step 3: Commit** `feat(api): add audit chain verification with approval checks`.

---

### Task W5-T08: Deploy `gate` with the OPA sidecar

**Requirement IDs:** ARC-001 (gate), POL-041, SEC-120 (gate rows), SEC-090 (allowed-upstream OPA image).
**Depends on:** W5-T05. **Branch:** `feat/w5-gate-deploy`.

- [ ] **Step 1: Image** — `services/gate/Dockerfile` (W2-T11 pattern) also copies `policies/opa/` into `/app/policies` and runs `opa build -b /app/policies -o /app/policies/bundle.tar.gz` in a build stage using the `opa-image` from `versions.yaml` (`COPY --from=<opa-image> /opa /usr/local/bin/opa` in the builder stage).
- [ ] **Step 2: Chart** — Deployment `gate`: init container (gate image, command `["cp", "/app/policies/bundle.tar.gz", "/policies/"]`) into `emptyDir` `/policies`; container `gate` (port 8080, env: `API_BASE`, `ARGOCD_SERVER`, `ARGOCD_TOKEN` from `argocd-api-tokens.gate`, `github-app-gate` secret, `GITOPS_AGENT_BOT_LOGIN`, `GITOPS_GATE_BOT_LOGIN`, `OWNER_GITHUB_LOGIN=arkhash0309`, `T0_CONFIDENCE_THRESHOLD` from `deploy/values/policy.yaml` (default 0.8), `CONSOLE_BASE_URL`, projected Keycloak token for `api:internal`); sidecar `opa` (image `openpolicyagent/opa@<digest>`, args `["run", "--server", "--addr=127.0.0.1:8181", "--bundle", "/policies/bundle.tar.gz"]`, resources 64Mi/128Mi, readiness `GET http://127.0.0.1:8181/health?bundles`); SA `gate` with no RoleBindings; NetworkPolicy rows from SEC-120 (egress to api, ArgoCD server, GitHub 443, Traefik for Keycloak, DNS; ingress from api on 8080 and observability on 8080).
- [ ] **Step 3: Deploy, verify readiness, update `capacity.md`; commit** `feat(deploy): deploy gate with OPA sidecar`.

---

### Task W5-T09: Manual safety-loop demo, capture complete, week 5 acceptance

**Requirement IDs:** MS-001 week 5, S3, S5, O-6, O-10.

- [ ] **Step 1 [PAID ≈ USD 0.15]: T0 demo** — `rootline-faultlab inject --scenario scn-v1-git-bad-image-tag-00` (payment, local debug); the alert-triggered system investigation proposes `revert_commit`; the gate classifies T0, merges, ArgoCD syncs, the proposal becomes `verified`; record proposal ID, PR URL, timestamps per stage and audit rows in `wiki/log.md`.
- [ ] **Step 2 [PAID ≈ USD 0.15]: T1 demo** — inject `scn-v1-git-bad-image-tag-03` (target `quote`) with `T0_CONFIDENCE_THRESHOLD=0.99` set temporarily in `deploy/values/policy.yaml` on a local feature branch tracked with `task up REVISION=<branch>` (this forces the `revert_commit` proposal to T1 via `confidence_below_threshold`); approve via the API with a step-up token (obtained with `scripts/dev_token.py --step-up`, which requests `acr_values=step-up&prompt=login` and needs the passkey) and an `Idempotency-Key`; assert `verified`; restore the threshold.
- [ ] **Step 3:** `rootline audit verify --check-approvals` → `chain_ok: true`, 0 violations.
- [ ] **Step 4:** Capture the remaining scenarios to 300 total (S3) including replacements (`rootline-faultlab generate --extend`) for excluded ones; `uv run rootline-eval dataset stats > wiki/eval/dataset.md` (wrapped in the page template) and `rootline-eval dataset test-half` → commit `eval/test-half.yaml`.
- [ ] **Step 5: Acceptance and release** — TST-POL-*, TST-API-001, TST-SEC-035 pass; `release: milestone 5`.
