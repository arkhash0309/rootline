# external-secrets

Status: not implemented yet — planned in W1-T10.

## Purpose

External Secrets Operator, which delivers every secret except the two ArgoCD repository Secrets (ADR 0032).

## Requirement IDs

SEC-100, SEC-101, SEC-082, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

ClusterSecretStores (including `pg-roles`), `Password` generators and ExternalSecrets in the `platform-config` Application (INF-020 wave -2).

## Configuration

1 replica in namespace `external-secrets`; memory request 64 Mi, limit 192 Mi (ARC-030).

## Dependencies

Kubernetes provider store in `rootline-secrets` locally; Google Secret Manager on GKE.

## Data owned

Generated Secrets such as `rootline-data/pg-<role>`.

## Failure modes and handling

Operator down: existing Secrets stay, new or rotated Secrets are not created, dependent pods stay `Pending` or `CreateContainerConfigError`.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
