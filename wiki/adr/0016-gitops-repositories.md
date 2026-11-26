# 0016 — GitOps repositories: `rootline` and `rootline-env`

Status: accepted
Date: 2026-11-26

## Context

Fault and fix commits are frequent and automated. If they landed in the portfolio repository, they would bury its history. They also need a narrow blast radius: the agent's GitHub App must be installable on a repository that contains only workload manifests.

This decision is row 0016 of the ADR index in spec §3. Primary reason recorded there: Fault and fix commits stay out of the portfolio repo history; clear blast radius.

## Decision

GitOps repositories: Platform manifests in `rootline` (`deploy/`); workload manifests in a separate repo `rootline-env`.

Spec §3 row 0016 is the source of this wording. It is implemented by requirement IDs GEN-010 to GEN-012, C4.

## Consequences

- Two deploy keys exist, one per repository.
- `rootline-env` accepts commits from bots only (spec §4.2) and ArgoCD tracks its `workload/` path.

## Alternatives considered

- A single repository: not chosen because of the history and blast-radius reasons in spec §3.

## Spec references

GEN-010 to GEN-012, C4; spec §3 row 0016.
