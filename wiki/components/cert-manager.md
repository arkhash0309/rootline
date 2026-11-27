# cert-manager

Status: configuration implemented in W1-T10 (`deploy/upstream/cert-manager/`, `deploy/charts/platform-config/`); not yet deployed to a cluster.

## Purpose

cert-manager issues the local CA, the wildcard certificate and, on GKE, Let's Encrypt certificates (spec §16.5, §16.6).

## Requirement IDs

INF-031, INF-041, SEC-011, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Rendered by `deploy/charts/platform-config/templates/ca.yaml` for `global.env` in `local` and `ci`:

| Object | Namespace | Content |
|---|---|---|
| ClusterIssuer `selfsigned` | cluster | `selfSigned: {}` |
| Certificate `rootline-local-ca` | `cert-manager` | `isCA: true`, `commonName: rootline-local-ca`, `duration: 87600h`, ECDSA 256, secret `rootline-local-ca`, issuer `selfsigned` |
| ClusterIssuer `rootline-ca` | cluster | `ca.secretName: rootline-local-ca` |
| Certificate `rootline-wildcard` | `kube-system` | `*.D` and `D` (`D` = `global.domain`, `127.0.0.1.sslip.io` locally), issuer `rootline-ca`, secret `rootline-wildcard-tls` |

Trust distribution (`templates/ca-configmap.yaml`, local and ci only): ArgoCD PostSync Job `copy-ca` in `cert-manager` runs `/bin/kubectl apply -k /work` with the image `docker.io/rancher/kubectl:v1.36.2@sha256:06c7a7a9772737494ae1e0c3af90f1b5385630c147e47c1c7cea92f4bed55fbe` (`kubectl-image` in `versions.yaml`; PG-22, ADR 0041; the image has no shell). `/work` is a read-only projected volume of ConfigMap `copy-ca-kustomization` (a `configMapGenerator` for ConfigMap `rootline-ca`, key `ca.crt`, in `rootline` and `keycloak`) and secret `rootline-local-ca` (item `ca.crt`). ServiceAccount `cert-manager/copy-ca` has Roles in `rootline` and `keycloak` (`create` on configmaps; `get`, `patch` on `rootline-ca`) and no Role in `cert-manager`. The GKE chain (`letsencrypt-prod`, INF-041) is not part of W1-T10.

## Configuration

3 pods in namespace `cert-manager`; memory requests controller 48 Mi, webhook 40 Mi, cainjector 40 Mi (`deploy/upstream/cert-manager/values-<env>.yaml`, `crds.enabled: true`); ARC-030 budget 128 Mi request, 384 Mi limit.

## Dependencies

Gateway API CRDs (INF-020 wave -4), Traefik Gateway. The `platform-config` Application (wave -2) needs the cert-manager CRDs from wave -3.

## Data owned

Certificate Secrets.

## Failure modes and handling

Certificate not `Ready` within 10 minutes on GKE: fall back to `rootline-ca` as described in INF-041. If secret `rootline-local-ca` does not exist when `copy-ca` starts, the pod stays in `ContainerCreating` until the secret exists or `activeDeadlineSeconds: 600` ends the Job; the next sync runs the hook again.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed (stage base): `helm template` of `platform-config` and `tests/repo/test_root_chart.py` pass. Not verified in a cluster (unverified 2026-11-27).
