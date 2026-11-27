# cert-manager

Status: not implemented yet — planned in W1-T10.

## Purpose

cert-manager issues the local CA, the wildcard certificate and, on GKE, Let's Encrypt certificates (spec §16.5, §16.6).

## Requirement IDs

INF-031, INF-041, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

ClusterIssuers `selfsigned` and `rootline-ca` (local, ECDSA P-256, CA valid 10 years), `letsencrypt-prod` (GKE, HTTP-01 through Gateway API); Certificate `rootline-wildcard` for `*.127.0.0.1.sslip.io`.

## Configuration

3 pods in namespace `cert-manager`; memory request 128 Mi total, limit 384 Mi total (ARC-030).

## Dependencies

Gateway API CRDs (INF-020 wave -4), Traefik Gateway.

## Data owned

Certificate Secrets.

## Failure modes and handling

Certificate not `Ready` within 10 minutes on GKE: fall back to `rootline-ca` as described in INF-041.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
