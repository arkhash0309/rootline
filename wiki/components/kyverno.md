# kyverno

Status: not implemented yet — planned in W1-T10.

## Purpose

Kyverno admission controller; W1-T10 installs it without policies, and the policies of SEC-090 follow in W3-T12.

## Requirement IDs

SEC-090, SEC-120, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Admission webhook in namespace `kyverno`; ClusterPolicies in `policies/kyverno/` (SEC-090).

## Configuration

Admission 1 replica, background 1; cleanup and reports controllers disabled; memory request 256 Mi total, limit 768 Mi total (ARC-001, ARC-030).

## Dependencies

kube-apiserver.

## Data owned

None.

## Failure modes and handling

Admission controller down: webhook failure policy decides whether resources are admitted; the SEC-090 policies document the setting in W3-T12.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
