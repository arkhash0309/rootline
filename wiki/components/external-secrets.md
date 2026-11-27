# external-secrets

Status: configuration implemented in W1-T10 (`deploy/upstream/external-secrets/`, `deploy/charts/platform-config/`); not yet deployed to a cluster.

## Purpose

External Secrets Operator, which delivers every secret except the two ArgoCD repository Secrets (ADR 0032).

## Requirement IDs

SEC-100, SEC-101, SEC-082, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Objects rendered by `deploy/charts/platform-config` (INF-020 wave -2), API group `external-secrets.io/v1`:

| Object | Namespace | Content |
|---|---|---|
| ClusterSecretStore `bootstrap` (local, ci) | cluster | Kubernetes provider, `remoteNamespace: rootline-secrets`, ServiceAccount `rootline-secrets/eso-bootstrap-reader`, CA from ConfigMap `kube-root-ca.crt` key `ca.crt` |
| Role and RoleBinding `eso-bootstrap-reader` (local, ci) | `rootline-secrets` | `get`, `list`, `watch` on Secret `rootline-bootstrap` |
| ClusterSecretStore `pg-roles` | cluster | Kubernetes provider, `remoteNamespace: rootline-data`, ServiceAccount `rootline-data/eso-pg-reader` (PG-10) |
| Role and RoleBinding `eso-pg-reader` | `rootline-data` | `get`, `list`, `watch` on the six Secrets `pg-rootline-migrator`, `pg-rootline-api`, `pg-rootline-agent`, `pg-rootline-faultlab`, `pg-rootline-console`, `pg-keycloak` |
| `Password` generators `password-48` (length 48) and `password-43` (length 43), both `digits: 8`, `symbols: 0`, `allowRepeat: true` | `rootline-data`, `rootline`, `keycloak`, `observability` | one pair per namespace, because a `generatorRef` is resolved in the namespace of the ExternalSecret |
| ExternalSecret `pg-<role>` (six, `refreshInterval: "0"`) | `rootline-data` | generates a password from `password-48` into a `kubernetes.io/basic-auth` Secret with `username: <role>` (underscored role name, for example `rootline_api`) |

Consumers derive a 32-byte AES key as `sha256(value)` (recorded in `wiki/components/api.md` by W4-T06).

## Configuration

1 replica in namespace `external-secrets`; memory requests controller 32 Mi, webhook 16 Mi, cert controller 16 Mi (`deploy/upstream/external-secrets/values-<env>.yaml`, `installCRDs: true`); ARC-030 budget 64 Mi request, 192 Mi limit.

## Dependencies

Kubernetes provider store in `rootline-secrets` locally; Google Secret Manager on GKE (store `gcp`, added in W7).

## Data owned

Generated Secrets such as `rootline-data/pg-<role>`.

## Failure modes and handling

Operator down: existing Secrets stay, new or rotated Secrets are not created, dependent pods stay `Pending` or `CreateContainerConfigError`.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed (stage base): `helm template` of `platform-config` and `tests/repo/test_root_chart.py` pass. Not verified in a cluster (unverified 2026-11-27).
