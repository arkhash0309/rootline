# kyverno

Status: installation configured in W1-T10 (`deploy/upstream/kyverno/`), no policies yet; not yet deployed to a cluster.

## Purpose

Kyverno admission controller; W1-T10 installs it without policies, and the policies of SEC-090 follow in W3-T12.

## Requirement IDs

SEC-090, SEC-120, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Admission webhook in namespace `kyverno`; ClusterPolicies in `policies/kyverno/` (SEC-090). Application `kyverno` (wave -3, chart `kyverno/kyverno`, version from `versions.yaml`).

## Configuration

`deploy/upstream/kyverno/values-<env>.yaml`: `admissionController.replicas: 1`, `backgroundController.replicas: 1`, `cleanupController.enabled: false`, `reportsController.enabled: false`; memory requests admission `160Mi` (`admissionController.container.resources`), background `96Mi` (`backgroundController.resources`). The chart default memory limit of the admission container (`384Mi`) is kept. ARC-030 budget: 256 Mi request, 768 Mi limit in total. The three values files have identical content.

## Dependencies

kube-apiserver.

## Data owned

None.

## Failure modes and handling

Admission controller down: webhook failure policy decides whether resources are admitted; the SEC-090 policies document the setting in W3-T12.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed (stage base): resource key paths checked against `helm show values kyverno --version 3.10.0`; `tests/repo/test_root_chart.py` passes. Not verified in a cluster (unverified 2026-11-27).
