# traefik

Status: not implemented yet — planned in W1-T10.

## Purpose

Ingress controller with Gateway API support: the k3s-bundled Traefik locally and a chart-installed Traefik on GKE (ADR 0021).

## Requirement IDs

INF-030, INF-031, INF-040, ARC-001. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Ports 80 and 443; HTTPRoutes for `console.D`, `auth.D`, `argocd.D` and optionally `shop.D` (INF-040).

## Configuration

Locally: `HelmChartConfig` in `infra/k3d/manifests/traefik-config.yaml` sets `providers.kubernetesGateway.enabled=true`, `ports.websecure.tls.enabled=true`, `deployment.replicas=1` (INF-030). Namespace `kube-system` locally and `traefik` on GKE.

## Dependencies

cert-manager certificates, Gateway API CRDs.

## Data owned

None.

## Failure modes and handling

Traefik down: console, Keycloak and ArgoCD are unreachable from the browser; in-cluster service-to-service traffic is unaffected.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
