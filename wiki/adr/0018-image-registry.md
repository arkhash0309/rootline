# 0018 — Image registry: Google Artifact Registry

Status: accepted
Date: 2026-11-26

## Context

Images must be pushed from GitHub Actions without long-lived credentials and pulled by GKE. The GitHub Container Registry has quota limits for private repositories. Artifact Registry in the persistent Terraform root costs very little.

This decision is row 0018 of the ADR index in spec §3. Primary reason recorded there: Private-repo GHCR quotas; tiny cost.

## Decision

Image registry: Google Artifact Registry repository in the persistent root, pushed by GitHub Actions via Workload Identity Federation. Local k3d uses locally built, imported images.

Spec §3 row 0018 is the source of this wording. It is implemented by requirement IDs INF-004, CI-001.

## Consequences

- CI authenticates through Workload Identity Federation (INF-004, CI-001).
- A cleanup policy removes old images; local k3d uses locally built images imported with `k3d image import`.

## Alternatives considered

- GitHub Container Registry (GHCR): not chosen because of the private-repository quotas named in spec §3.

## Spec references

INF-004, CI-001; spec §3 row 0018.
