# 0017 — Manifest tooling: Helm everywhere, workload rendered once

Status: accepted
Date: 2026-11-26

## Context

One templating system keeps the repository understandable. Fault and fix diffs on the workload must be exact line changes, which plain YAML provides and rendered-on-sync templates do not.

This decision is row 0017 of the ADR index in spec §3. Primary reason recorded there: One templating system; plain YAML makes fault and fix diffs exact.

## Decision

Manifest tooling: Helm everywhere. Upstream charts plus one Rootline umbrella chart; per-environment values files. Workload manifests are rendered once to plain YAML.

Spec §3 row 0017 is the source of this wording. It is implemented by requirement IDs WKL-010, C5.

## Consequences

- The workload is rendered once by `scripts/render_workload.py` into plain YAML (WKL-010) and re-rendering is a PR to `rootline-env`.
- Platform components use upstream charts plus one umbrella chart with per-environment values files.

## Alternatives considered

- Kustomize: not chosen because spec §3 requires one templating system.

## Spec references

WKL-010, C5; spec §3 row 0017.
