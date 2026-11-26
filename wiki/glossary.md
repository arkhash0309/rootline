# Glossary

This table is the table of spec §2 (`docs/superpowers/specs/2026-11-25-rootline-design.md`), copied verbatim on 2026-11-27. Terms are used with exactly these meanings throughout.

| Term | Definition |
|---|---|
| **Workload** | The trimmed OpenTelemetry Demo application running in namespace `shop`. It is the system under diagnosis. |
| **Platform** | All Rootline components plus their infrastructure dependencies (Keycloak, Postgres, observability, ArgoCD, Kyverno, Chaos Mesh, External Secrets, cert-manager). |
| **Fault type** | A named, parameterisable way of breaking the workload, for example `bad-image-tag`. Listed in §7.2. |
| **Scenario** | One concrete, seeded instance of a fault type with fixed parameters (target, intensity, background load, adversarial modifier). Identified by `scenario_id`. |
| **Scenario run** | One live execution of a scenario by the Fault Lab, producing at most one snapshot. |
| **Snapshot** | The captured, immutable bundle of telemetry, Kubernetes state and Git history for one scenario run (§7.7). |
| **Label** | Ground truth for a scenario: root-cause entities, fault category, acceptable actions, and the other fields in §7.6. |
| **Incident** | A platform record grouping one or more alerts about a problem in the workload (§12.6). |
| **Investigation** | One execution of the agent state machine for an incident (§9.2). An incident may have several investigations. |
| **Step** | One node execution inside an investigation (for example `triage`). |
| **Tool call** | One invocation of an MCP tool by the agent. Identified by `tool_call_id` (ULID). |
| **Evidence ref** | A reference from a report claim to a `tool_call_id`, plus an optional JSON pointer into the tool output. |
| **Report** | The structured root-cause report produced by node `rca` and checked by node `verify` (§9.4). |
| **Proposal** | A typed fix chosen from the action catalogue (§11.3), rendered into a PR or a sync request, and evaluated by the gate. |
| **Tier** | The policy classification of a proposal: `T0`, `T1`, `T2` or `DENIED` (§11.4). |
| **Gate** | The service that evaluates proposals with OPA, manages approvals, merges PRs, triggers ArgoCD sync and verifies recovery (§11). |
| **Live mode** | MCP servers answer from the running cluster, Prometheus, Loki, Tempo, ArgoCD and GitHub. |
| **Replay mode** | MCP servers answer from a snapshot bundle (§8.5). |
| **Configuration (model config)** | A named mapping from agent node to model and effort (§9.5). |
| **Sweep** | One evaluation of one or more configurations over a split (§15.8). |
| **Domain (`D`)** | The base DNS name of an environment: `127.0.0.1.sslip.io` locally, `<ip-with-dashes>.sslip.io` on GKE (§16.6). |
| **Owner** | The repository owner, the single human user of the system and the only approver in practice. |
| **ULID** | Universally Unique Lexicographically Sortable Identifier, 26 characters, Crockford base32. All Rootline primary keys are ULIDs stored as `text`, except where §13 says otherwise. |

## Additions

Terms that are not in spec §2 are added to this table with the date and the pull request that introduced them.

| Term | Definition | Added on | Introduced by |
|---|---|---|---|
