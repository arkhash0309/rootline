# 0028 — Planning schedule adjustments for weeks 2 to 4

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-3, PG-4, PG-7 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-3 (spec reference SEC-080, §22): Git-channel captures start in week 2, but the GitHub Apps are scheduled for week 3.

PG-4 (spec reference INF-023, MCP-060, MCP-020–022, AGT-083, LAB-046): Week-2 Fault Lab work needs pieces scheduled after week 2: ArgoCD accounts (restore via sync), redaction (LAB-062), anomaly algorithms (LAB-044), the injection detector (TST-LAB-007). LAB-046 needs auth from week 3.

PG-7 (spec reference EVL-080, CI-010): The CI smoke gate downloads snapshots from GCS through WIF, but the persistent GCP root is created in week 7.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-3: Create `rootline-faultlab` (O-5) in week 2; `rootline-agent`, `rootline-gate` and ruleset `protect-main` stay in week 3.

PG-4: Build `argocd-accounts`, `rootline_mcpkit.redact`, `rootline_mcp_telemetry.algorithms`/`scan` and `rootline_agent.guard.detect_injection` in week 2. Build LAB-046 in week 3 (W3-T11).

PG-7: `eval-smoke.yml` is added in week 4 and its job is skipped with a notice when repository variable `GCP_WIF_PROVIDER` is empty. It becomes active in W7-T01. Until then, the owner runs `task eval:smoke` locally before merging PRs in the EVL-080 path list and pastes the summary into the PR.

## Consequences

- The `rootline-faultlab` GitHub App is created in week 2; `rootline-agent`, `rootline-gate` and ruleset `protect-main` stay in week 3.
- `argocd-accounts`, redaction, the anomaly algorithms and the injection detector are built in week 2; LAB-046 is built in week 3 (W3-T11).
- The `eval-smoke.yml` job is gated on repository variable `GCP_WIF_PROVIDER` until W7-T01.

## Alternatives considered

- Follow the milestone table of spec §22 literally: not chosen because the week-2 Fault Lab would need pieces that the table schedules in week 3 and week 4 (PG-3, PG-4).

## Spec references

PG-3, PG-4, PG-7; spec §26 rows PG-3, PG-4, PG-7; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
