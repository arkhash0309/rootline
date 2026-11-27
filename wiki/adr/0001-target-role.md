# 0001 — Target role: AI / LLM Engineer

Status: accepted
Date: 2026-11-26

## Context

Rootline is a portfolio artifact (goals G1 to G5 in spec §1.4) that recruiters and interviewers for AI/LLM Engineer roles read within 3 minutes and that must survive a 60-minute technical deep-dive (spec §1.3). Spec §3 gives the primary reason as the owner's career goal and the highest 2026 demand for that role. The target role decides which skills the project must demonstrate, so it has to be fixed before any feature is scoped.

This decision is row 0001 of the ADR index in spec §3. Primary reason recorded there: Owner's career goal; highest 2026 demand.

## Decision

Target role: AI / LLM Engineer.

Spec §3 row 0001 is the source of this wording. It is implemented by requirement IDs §1.3, G1.

## Consequences

- Every feature must show LLM engineering depth: structured agent, model routing, grounding, guardrails, measured evaluation and cost control (goal G1).
- Success criteria S4 (benchmark report), S5 (policy safety) and S6 (prompt-injection resistance) in spec §1.6 are written to make that depth measurable.

## Alternatives considered

- ML research engineer: not chosen because it does not match the owner's career goal named in spec §3, and the project excludes GPU inference (NG5) and fine-tuning (NG4).
- Data scientist: not chosen because it does not match the owner's career goal named in spec §3; the artifact is a running system, not an analysis.

## Spec references

§1.3, G1; spec §3 row 0001.
