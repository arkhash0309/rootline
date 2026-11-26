# Rootline Implementation Plan — Week 8: Polish and Publish

> **For agentic workers:** Execute this week with the swarm protocol in `2026-11-26-rootline-00-overview.md` §7: the Haiku 5.5 coordinator runs the stages in the **Execution schedule** below, dispatching Sonnet 5.5 implementers (high effort, one worktree per task in parallel stages), Opus 5.5 reviewers (high effort) and, when re-planning is needed, the Opus 5.5 planner (high effort) — `CLAUDE.md` → "Agent models and roles". Within each task, follow superpowers:subagent-driven-development's discipline (implement → spec-compliance review → code-quality review). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Final benchmark numbers (sweep 2), an honest final report with failure analysis, the full threat model, the public dataset prepared for Hugging Face, the technical write-up, README and demo video, and verified success criteria S1–S9.

**Architecture:** No new services. Work is analysis (dev split only before sweep 2), documentation, and one owner-run publication.

**Tech Stack:** `rootline-eval`, `huggingface_hub` (owner-run upload), Markdown, SVG.

## Global Constraints

All constraints in `2026-11-26-rootline-00-overview.md` → "Global Constraints" apply. Week-specific additions:

- **EVL-011:** fixes after sweep 1 are driven only by dev-split failure analysis. The sweep-1 test report is not used to choose changes.
- **Write-up and README claims (DEL-003):** every claim carries a number or a link to evidence; "better/worse" only with Holm p < 0.05 (EVL-040).
- Publication to Hugging Face and the video are owner actions (O-14, O-15).
- Week 8 acceptance (MS-001): S3–S9 verified; README per §24.1; video recorded; write-up committed.


## Execution schedule

Mirrors `2026-11-26-rootline-schedule.yaml` (week 8); `uv run python scripts/swarm_schedule.py table --week 8` must print exactly this table. Parallel stages run in separate worktrees (at most 3 implementers at once), then pass the integration gate (overview §7.6–§7.7) before one squash-merged PR reaches `develop`. Owned paths per task are listed in the YAML only. Deferred steps (overview §7.3) run at the start of the named sequential stage.

| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |
|---|---|---|---|---|
| W8-P1 | parallel | — | W8-T04 (`docs/w8-threat-model`); W8-T05 (`feat/w8-publish-hf`) | W8-T05 steps 3 → W8-S2 |
| W8-S1 | sequential | W8-P1 | W8-T01 (`feat/w8-dev-fixes`); W8-T02 (no branch) | — |
| W8-P2 | parallel | W8-S1 | W8-T03 (`docs/w8-cost-ledger`); W8-T06 (`docs/w8-writeup`) | W8-T06 steps 5 → W8-S2 |
| W8-S2 | sequential | W8-P2 | W8-T07 (no branch) | — |

---

### Task W8-T01: Dev-split failure analysis and dev-only fixes

**Requirement IDs:** EVL-011, EVL-060 (sweep 2 precondition), EVL-090 §8 (failure modes), R5.
**Depends on:** W7-T08.

- [ ] **Step 1 [PAID ≈ USD 6 batch]:** `rootline-eval run --config routed --split dev --batch` (full dev, 157) and `all-small` dev; `rootline-eval report` on the dev runs.
- [ ] **Step 2:** owner labels every incorrect dev `routed` scenario with one failure mode from the EVL-090 list in `eval/failure-modes/<dev run_id>.yaml`; the agent drafts suggested labels with evidence links (tool-call IDs, report claims) in `eval/failure-modes/<dev run_id>.draft.yaml` for the owner to accept or edit.
- [ ] **Step 3:** for the two most frequent modes, implement targeted dev-only changes (prompt version bumps, e.g. `rca.v2`; MCP-023 algorithm parameter changes with dev evidence in the PR; budget defaults) — each in its own PR with before/after dev metrics on the affected scenarios (≤ 40 per iteration, EVL-060). Bumping `tool_layer_version` is not allowed this week (it would invalidate snapshots).
- [ ] **Step 4:** re-run T0 calibration (W7-T10) on the final dev routed run if prompts changed. Commit each change with the wiki updates.

---

### Task W8-T02: Sweep 2 and the final report

**Requirement IDs:** EVL-060 (sweep 2), EVL-063, EVL-090, EVL-031, S4, O-14.
**Depends on:** W8-T01.

- [ ] **Step 1 [PAID, projected ≈ USD 9.5] (O-14):** `eval/sweeps/sweep2.yaml` = `baseline`, `all-small`, `routed` on `test`; run with the cost gate and `ROOTLINE_FINAL_SWEEP=1`.
- [ ] **Step 2:** owner labels incorrect `routed` test scenarios (failure modes) in `eval/failure-modes/<sweep2 routed run_id>.yaml`; owner writes `eval/limitations.md` (EVL-090 §10 minimum topics).
- [ ] **Step 3:** `rootline-eval report --final <sweep-2 runs> <sweep-1 runs for all-large, local and ablations>` → `eval/reports/final/report.md` with each number labelled by its sweep; `--final` fails on missing failure-mode labels or limitations. Review against the EVL-090 checklist (S4) and record the review in the release PR.
- [ ] **Step 4:** `rootline-eval judge` and `langfuse-sync` for the sweep-2 routed run; import runs into the API; update `wiki/eval/results.md` (headline table + link).

---

### Task W8-T03: Cost reconciliation (S8)

**Requirement IDs:** CST-012, S8, CST-013.

- [ ] **Steps:** owner pastes Anthropic Console usage per key and the GCP billing report total into `wiki/cost-ledger.md`; the agent adds ledger totals (`rootline-llm budget show`), Actions minutes (`gh api /repos/arkhash0309/rootline/actions/cache/usage` and the billing page figure pasted by the owner), Langfuse units (host ledger + `core.langfuse_usage`), and a final table: line, cap, actual, variance; total ≤ USD 100 (S8). If any free tier was exceeded, record the response taken (CST-013).

---

### Task W8-T04: Threat model (SEC-140)

**Requirement IDs:** SEC-140, T1–T14, S9.

- [ ] **Steps:** write `wiki/security/threat-model.md` as a full STRIDE analysis: system diagram with trust boundaries (browser ↔ console, console ↔ api, agent ↔ MCP servers, agent ↔ Anthropic/Langfuse, gate ↔ GitHub/ArgoCD, faultlab ↔ cluster, CI ↔ GCP); for each of T1–T14 a section with: description, STRIDE category, attack path, mitigations (requirement IDs), verifying tests (test IDs) with the latest result and date, residual risk, and evidence links (W3-T12 checks, W7-T03/T04 cosign and Kyverno outputs, injection-resistance numbers from the final report for T1). Add any new threat found during implementation as T15+. Commit `docs(security): add full threat model`.

---

### Task W8-T05: Public dataset (Rootline-Bench) preparation

**Requirement IDs:** EVL-100, TST-SEC-031, LAB-062, O-14.
**Depends on:** W8-T02. **Branch:** `feat/w8-publish-hf`.

- [ ] **Step 1: TST-SEC-031 first** — test: `publish_hf.prepare(out_dir, snapshots)` on a fixture snapshot with an injected secret in `logs.parquet` (`sk-ant-...`) and in `k8s/objects.json` → raises `RedactionFinding` listing file and kind, and writes nothing; clean fixture → writes the dataset layout.
- [ ] **Step 2: Implement `rootline-eval publish-hf`** with two phases: `prepare` (default) builds `data/hf/rootline-bench/` with `scenarios.v1.jsonl` (labels joined with resolved run records), `snapshots/<scenario_id>.tar.zst` (latest captured run per scenario), `README.md` data card (motivation, composition with the S3 table, collection process (LAB-041), redaction procedure (MCP-060 rules + `redaction_version`), splits and held-out types, licence CC BY 4.0, limitations, intended and out-of-scope uses, citation), `LICENSE` (CC BY 4.0 text); re-runs `redact` over every text column and JSON/text file and fails on any finding; `upload` phase (`--upload`, owner only) uses `huggingface_hub.HfApi().upload_folder(repo_id=f"{HF_USER}/rootline-bench", repo_type="dataset", folder_path=...)` after printing the file list and total size and asking for `yes`.
- [ ] **Step 3 [OWNER] (O-14):** review the data card; run `rootline-eval publish-hf --upload`; record the dataset URL in `wiki/eval/results.md` and README.

---

### Task W8-T06: Write-up, README, architecture SVG and demo video

**Requirement IDs:** DEL-001, DEL-002, DEL-003, G5, O-15.

- [ ] **Step 1: Architecture SVG** — `docs/writeup/architecture.svg` drawn from §5.1 (load the `artifact-diagramming` skill guidance for legibility in light and dark themes, or hand-author the SVG); text labels as text, not paths.
- [ ] **Step 2: Live-screen GIF** — record a 30 s GIF of the live investigation screen from the T0 demo (local), ≤ 8 MB, `docs/writeup/live-investigation.gif`.
- [ ] **Step 3: README (DEL-001)** — the 11 sections in order with real numbers from `eval/reports/final/report.md` (top-1 with CI for baseline, all-small, routed, all-large, local; cost per investigation; injection resistance), links to runbooks, report, threat model, dataset; "Why this project" ≤ 150 words.
- [ ] **Step 4: Write-up (DEL-003)** — `docs/writeup/rootline.md`, 2,500–4,000 words (count with `uv run python -c "import re,sys;print(len(re.findall(r'\\w+', open(sys.argv[1]).read())))" docs/writeup/rootline.md`), the eight sections, each claim linked to evidence.
- [ ] **Step 5 [OWNER] (O-15): Video** — record ≤ 3 min following DEL-002's timeline on a GKE session (`task gke:up` beforehand, `task gke:down` after); upload as an unlisted video; link it in README. `wiki/runbooks/interview-demo.md` documents the exact click path, the accounts used (owner, interviewer for T2), and the fallback to the local cluster.
- [ ] **Step 6: Commit** `docs: add README, technical write-up and demo materials`.

---

### Task W8-T07: Final verification of S1–S9 and release

**Requirement IDs:** S1–S9, MS-001 week 8, MS-002.

- [ ] **Step 1: Verify each criterion and link evidence in the release PR**

| ID | Verification |
|---|---|
| S1 | W7-T06 timing record; a fresh `task gke:up` + `task gke:down` this week with leak checks empty |
| S2 | `task doctor` on a fresh `task down && task up` → `memory_requests_total ≤ 9.5` and all apps healthy |
| S3 | `rootline-eval dataset stats` committed in `wiki/eval/dataset.md`; test split = held-out types per §15.2 |
| S4 | `eval/reports/final/report.md` reviewed against EVL-090 |
| S5 | `uv run pytest -k tst_pol -v`, `opa test policies/opa -v` green; `rootline audit verify --check-approvals` → 0 violations on local and on the last GKE session's log |
| S6 | final report `injection_resistance` = 1.0 for `routed` on test; if < 1.0, the criterion is reported as **not met** with the failing scenarios analysed (no hiding) |
| S7 | `e2e.yml` green on the `release: milestone 8` PR (or the TST-071 local report attached) |
| S8 | W8-T03 ledger total ≤ USD 100 |
| S9 | `task wiki:lint` passes; `status.md` says Week 8 — Polish and publish; ADRs 0001–0025 plus all added ADRs present |

- [ ] **Step 2:** final `status.md` (all tasks Done, "Next" lists MS-004 future work), `log.md`, cost ledger; `release: milestone 8` PR into `main`, merged by the owner with a merge commit.
