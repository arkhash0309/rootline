# traefik

Status: configuration implemented in W1-T10 (`infra/k3d/manifests/traefik-config.yaml`, Gateway in `deploy/charts/platform-config`); not yet deployed to a cluster.

## Purpose

Ingress controller with Gateway API support: the k3s-bundled Traefik locally and a chart-installed Traefik on GKE (ADR 0021).

## Requirement IDs

INF-030, INF-031, INF-040, SEC-011, ARC-001. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Client ports 80 and 443 (Service `traefik` maps them to the entry points `web` `:8000` and `websecure` `:8443`, ADR 0046 T9); HTTPRoutes for `console.D`, `auth.D`, `argocd.D` and optionally `shop.D` (INF-040).

Gateway `rootline` (`deploy/charts/platform-config/templates/gateway.yaml`): namespace `kube-system` on local and ci, `traefik` on gke; `gatewayClassName: traefik`; listener `http` (port 8000, the `web` entry point) and listener `https` (port 8443, the `websecure` entry point, TLS `Terminate`, certificate Secret `rootline-wildcard-tls`); both with `allowedRoutes.namespaces.from: All`.

In-cluster name resolution (SEC-011, local and ci): ConfigMap `coredns-custom` in `kube-system`, key `rootline.override`, rewrites `auth.D`, `console.D` and `argocd.D` to `traefik.kube-system.svc.cluster.local`.

## Configuration

Locally: `HelmChartConfig` in `infra/k3d/manifests/traefik-config.yaml` sets `deployment.replicas=1`, `gateway.enabled=false` (no chart-default Gateway `traefik-gateway`; GatewayClass `traefik` is still created), `providers.kubernetesGateway.enabled=true` and `ports.websecure.http.tls.enabled=true` (INF-030, ADR 0046 T9); k3d mounts the directory into `/var/lib/rancher/k3s/server/manifests/rootline`. Namespace `kube-system` locally and `traefik` on GKE. Application `traefik` (chart `traefik/traefik`, version from `versions.yaml`, namespace `traefik`) renders for `gke` only; its values file `deploy/upstream/traefik/values-gke.yaml` does not exist yet and is added in W7.

Verified (2026-11-27, ADR 0046 T9): Traefik matches Gateway listeners to its entry points by port; the entry points listen on 8000 and 8443 inside the pod, so the listener ports are 8000 and 8443. HTTPRoute `parentRefs` that name a port use 8000 or 8443.

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
