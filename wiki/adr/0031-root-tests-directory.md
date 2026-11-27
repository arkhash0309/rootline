# 0031 — Root `tests/` directory for cross-cutting tests

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-8 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-8 (spec reference GEN-001, SEC-053, TST-070): SEC-053 (`tests/fixtures/keys/`) and TST-070 (`tests/e2e/`) imply a root `tests/` directory that GEN-001 does not list.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-8: Root `tests/` is allowed and holds only cross-cutting tests: `tests/repo/` (layout and contract tests), `tests/fixtures/`, `tests/e2e/`. Package tests stay next to their package.

## Consequences

- Root `tests/` holds only `tests/repo/`, `tests/fixtures/` and `tests/e2e/`.
- Package tests stay next to their package.

## Alternatives considered

- Put end-to-end tests under `scripts/`: not chosen because SEC-053 and TST-070 name the paths `tests/fixtures/keys/` and `tests/e2e/` (PG-8).

## Spec references

PG-8, GEN-001, SEC-053, TST-070; spec §26 rows PG-8; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
