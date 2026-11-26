# Threat model

Status: summary only — full STRIDE in W8-T04.

The table is the SEC-140 table of spec §10.15, copied verbatim on 2026-11-27. Each threat lists its mitigation IDs; test IDs are added by W8-T04.

| # | Threat | STRIDE | Mitigations |
|---|---|---|---|
| T1 | Prompt injection via logs, events or commit messages leads to a harmful fix | Tampering / EoP | AGT-002, AGT-080/081, AGT-082, AGT-083, POL tiers, LAB-070 measurement |
| T2 | LLM hallucinates evidence to justify a fix | Repudiation | AGT-003, AGT-025 |
| T3 | Stolen user token used by the agent beyond intent | Spoofing | SEC-044 short-lived encrypted storage; SEC-043 audience-bound 10-minute tokens |
| T4 | Confused deputy: a token for one MCP server used at another | Spoofing | SEC-050 `aud` check |
| T5 | Agent self-escalation via a PR changing RBAC, policies or its own config | EoP | POL Denied class; AppProject blacklist; Kyverno `workload-confinement`; agent app installed only on `rootline-env` |
| T6 | Bypassing approval by merging directly | EoP | SEC-081 ruleset; agent app not a bypass actor; SEC-132 check |
| T7 | Supply-chain image tampering | Tampering | SEC-090 signature verification (gke); digest-pinned upstream |
| T8 | Secret leakage to the LLM provider or Langfuse | Information disclosure | MCP-060 redaction; MCP-061 allowlist; OBS-022 masking |
| T9 | Audit log tampering | Repudiation | SEC-130 hash chain; no write grants |
| T10 | Ground-truth leakage to the agent (benchmark validity) | Information disclosure | ARC-011; LAB-022 commit-message rules; chaos CRs in `rootline-lab` |
| T11 | Runaway LLM spend | Denial of service (financial) | AGT-020; CST-010/011; prepaid credit cap |
| T12 | CSRF or session theft in the console | Spoofing / Tampering | UI-005 cookie flags; CSRF token; BFF |
| T13 | Webhook spoofing (fake alerts) | Spoofing | API-040 bearer tokens; NetworkPolicy source restriction |
| T14 | Auto-merge storm (many T0 merges) | DoS / Tampering | POL-031 circuit breaker |
