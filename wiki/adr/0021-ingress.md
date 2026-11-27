# 0021 — Ingress: Traefik with Gateway API

Status: accepted
Date: 2026-11-26

## Context

The console, Keycloak and ArgoCD need HTTPS ingress in both environments with identical route definitions. k3s bundles Traefik, and Gateway API `HTTPRoute` is the successor of Ingress. The ingress-nginx project is retired.

This decision is row 0021 of the ADR index in spec §3. Primary reason recorded there: Parity; ingress-nginx is retired.

## Decision

Ingress: Traefik with Gateway API (`HTTPRoute`) in both environments.

Spec §3 row 0021 is the source of this wording. It is implemented by requirement IDs INF-030, INF-040.

## Consequences

- The same HTTPRoutes are used locally and on GKE (INF-030, INF-040).
- Locally Traefik is the k3s bundle configured by a `HelmChartConfig`; on GKE it is installed from a chart.

## Alternatives considered

- ingress-nginx: not chosen because the project is retired (spec §3).
- Gateway API with Envoy: not chosen because Traefik with Gateway API gives the same parity in both environments (spec §3 reason) and is bundled with k3s.

## Spec references

INF-030, INF-040; spec §3 row 0021.
