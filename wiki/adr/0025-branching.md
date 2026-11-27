# 0025 — Branching: Git flow light

Status: accepted
Date: 2026-11-26

## Context

The owner instructed on 2026-11-25 that the repository uses a lightweight Git flow: `main` for releases, `develop` for integration and short-lived feature, fix and docs branches.

This decision is row 0025 of the ADR index in spec §3. Primary reason recorded there: Owner instruction (2026-11-25).

## Decision

Branching: Git flow light: `main` (releases), `develop` (integration), `feat/*` / `fix/*` / `docs/*` from `develop`.

Spec §3 row 0025 is the source of this wording. It is implemented by requirement IDs GEN-020.

## Consequences

- Each week ends with a release PR `develop` to `main`, titled `release: milestone <N>` (GEN-021).
- Squash merge into `develop`; merge commit into `main`.

## Amendment 2026-11-27 (PG-26, ADR 0045)

GEN-020 (spec §4.3) table row `main`, column "Protection", no longer lists "linear history". The cell now reads: "Ruleset: PR required; required checks `ci / required`; no force-push; no deletion; no linear-history rule (GEN-021 release merge commits; PG-26, ADR 0045); bypass: owner only". Reason: a `required_linear_history` rule rejects merge commits, and GEN-021 merges the release PR `develop → main` with a merge commit; GEN-021 wins because it is the more specific rule. `.github/rulesets/main.json` and `.github/rulesets/develop.json` have no `required_linear_history` rule. No other GEN-020 row and no part of GEN-021 changed. Details: `wiki/adr/0045-w1-t14-ci-decisions.md` D4.

## Alternatives considered

- Trunk-based development: not chosen because of the owner instruction of 2026-11-25.

## Spec references

GEN-020, GEN-021, PG-26; spec §3 row 0025; ADR 0045.
