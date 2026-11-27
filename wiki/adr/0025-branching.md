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

## Alternatives considered

- Trunk-based development: not chosen because of the owner instruction of 2026-11-25.

## Spec references

GEN-020; spec §3 row 0025.
