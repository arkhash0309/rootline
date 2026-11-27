# traefik

Status: configuration implemented in W1-T10 (`infra/k3d/manifests/traefik-config.yaml`, Gateway in `deploy/charts/platform-config`); not yet deployed to a cluster.

## Purpose

Ingress controller with Gateway API support: the k3s-bundled Traefik locally and a chart-installed Traefik on GKE (ADR 0021).

## Requirement IDs

INF-030, INF-031, INF-040, SEC-011, ARC-001. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Ports 80 and 443; HTTPRoutes for `console.D`, `auth.D`, `argocd.D` and optionally `shop.D` (INF-040).

Gateway `rootline` (`deploy/charts/platform-config/templates/gateway.yaml`): namespace `kube-system` on local and ci, `traefik` on gke; `gatewayClassName: traefik`; listener `http` (port 80) and listener `https` (port 443, TLS `Terminate`, certificate Secret `rootline-wildcard-tls`); both with `allowedRoutes.namespaces.from: All`.

In-cluster name resolution (SEC-011, local and ci): ConfigMap `coredns-custom` in `kube-system`, key `rootline.override`, rewrites `auth.D`, `console.D` and `argocd.D` to `traefik.kube-system.svc.cluster.local`.

## Configuration

Locally: `HelmChartConfig` in `infra/k3d/manifests/traefik-config.yaml` sets `providers.kubernetesGateway.enabled=true`, `ports.websecure.tls.enabled=true`, `deployment.replicas=1` (INF-030); k3d mounts the directory into `/var/lib/rancher/k3s/server/manifests/rootline`. Namespace `kube-system` locally and `traefik` on GKE. Application `traefik` (chart `traefik/traefik`, version from `versions.yaml`, namespace `traefik`) renders for `gke` only; its values file `deploy/upstream/traefik/values-gke.yaml` does not exist yet and is added in W7.

Unverified (2026-11-27): Traefik matches Gateway listeners to its entry points by port. The plan fixes listener ports 80 and 443 (W1-T10 Step 5); if the bundled Traefik entry points listen on 8000 and 8443 inside the pod, the Gateway is not accepted and the bring-up in W1-T12 must change the listener ports.

## Dependencies

cert-manager certificates, Gateway API CRDs.

## Data owned

None.

## Failure modes and handling

Traefik down: console, Keycloak and ArgoCD are unreachable from the browser; in-cluster service-to-service traffic is unaffected.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed (stage base): `helm template` of `platform-config` and `tests/repo/test_root_chart.py` pass. Not verified in a cluster (unverified 2026-11-27).
