# Architecture

Living architecture page, linked to the spec (`docs/superpowers/specs/2026-11-25-rootline-design.md`). Last updated 2026-11-27. The spec states what must be true; this page and the component pages state what is true now (WIK-001).

## Context diagram

Verbatim from spec §5.1:

```
                        ┌────────────────── Browser (owner / interviewer) ──────────────────┐
                        │  console.D  (Next.js UI + BFF)        auth.D (Keycloak)  argocd.D │
                        └────────┬───────────────────────────────────┬───────────────────────┘
                                 │ HTTPS (Traefik, Gateway API)      │
 ┌───────────────────────────────▼───────────────────────────────────▼──────────────────────────────┐
 │ Kubernetes cluster (k3d locally / GKE)                                                            │
 │                                                                                                   │
 │  ns rootline:  console ──► api ──► Postgres (ns rootline-data)                                    │
 │                 api ──► faultlab        api ──► gate (reevaluate)                                 │
 │                 agent (workers) ──MCP/OAuth──► mcp-telemetry ──► Prometheus/Loki/Tempo            │
 │                                 ──MCP/OAuth──► mcp-k8s ───────► kube-apiserver (read-only)        │
 │                                 ──MCP/OAuth──► mcp-gitops ────► GitHub rootline-env (App: agent)  │
 │                 agent ──HTTPS──► Anthropic API / (Ollama on host, eval only)                     │
 │                 agent, api, gate ──OTLP──► Langfuse Cloud (agent traces only, §20.3)              │
 │                 gate ──► OPA (sidecar) ; gate ──► GitHub (App: gate) ; gate ──► ArgoCD API         │
 │                 faultlab ──► kube-apiserver (flags, chaos CRs) ; faultlab ──► GitHub (App: lab)   │
 │  ns keycloak:   Keycloak ──► Postgres                                                             │
 │  ns observability: otel-collector, Prometheus, Alertmanager ──webhook──► api, Loki, Tempo         │
 │  ns shop:       trimmed OpenTelemetry Demo (the workload)                                         │
 │  ns argocd:     ArgoCD ──► GitHub rootline (platform) + rootline-env (workload)                   │
 │  ns chaos-mesh, ns rootline-lab (Chaos CRs), ns kyverno, ns external-secrets, ns cert-manager     │
 └───────────────────────────────────────────────────────────────────────────────────────────────────┘
 Host (owner laptop, eval only): rootline-eval CLI + replay MCP servers in-process + Ollama
```

## Components

The platform consists of exactly the components of ARC-001. Extra component pages: [components/telemetry.md](components/telemetry.md) and [components/capacity.md](components/capacity.md).

| Component | Namespace | Spec | Wiki page |
|---|---|---|---|
| `console` | `rootline` | ARC-001, §14 | [components/console.md](components/console.md) |
| `api` | `rootline` | ARC-001, §12 | [components/api.md](components/api.md) |
| `agent` | `rootline` | ARC-001, §9 | [components/agent.md](components/agent.md) |
| `gate` | `rootline` | ARC-001, §11 | [components/gate.md](components/gate.md) |
| `faultlab` | `rootline` | ARC-001, §7 | [components/faultlab.md](components/faultlab.md) |
| `mcp-telemetry` | `rootline` | ARC-001, §8.2 | [components/mcp-telemetry.md](components/mcp-telemetry.md) |
| `mcp-k8s` | `rootline` | ARC-001, §8.3 | [components/mcp-k8s.md](components/mcp-k8s.md) |
| `mcp-gitops` | `rootline` | ARC-001, §8.4 | [components/mcp-gitops.md](components/mcp-gitops.md) |
| `migrate` | `rootline` | ARC-001, §13 | [components/migrate.md](components/migrate.md) |
| `demo-seed` | `rootline` | ARC-001, §16.7 | [components/demo-seed.md](components/demo-seed.md) |
| Postgres | `rootline-data` | ARC-001, §13 | [components/postgres.md](components/postgres.md) |
| Keycloak | `keycloak` | ARC-001, §10.2 | [components/keycloak.md](components/keycloak.md) |
| keycloak-config | `keycloak` | ARC-001, SEC-012 | [components/keycloak-config.md](components/keycloak-config.md) |
| OTel Collector | `observability` | ARC-001, WKL-020 | [components/otel-collector.md](components/otel-collector.md) |
| Prometheus + Alertmanager + kube-state-metrics + operator | `observability` | ARC-001, WKL-021 | [components/kube-prometheus-stack.md](components/kube-prometheus-stack.md) |
| Loki | `observability` | ARC-001, WKL-020 | [components/loki.md](components/loki.md) |
| Tempo | `observability` | ARC-001, WKL-022 | [components/tempo.md](components/tempo.md) |
| ArgoCD | `argocd` | ARC-001, SEC-110, §16.4 | [components/argocd.md](components/argocd.md) |
| Chaos Mesh | `chaos-mesh` | ARC-001, §7.3 | [components/chaos-mesh.md](components/chaos-mesh.md) |
| Kyverno | `kyverno` | ARC-001, SEC-090 | [components/kyverno.md](components/kyverno.md) |
| External Secrets Operator | `external-secrets` | ARC-001, SEC-100 | [components/external-secrets.md](components/external-secrets.md) |
| cert-manager | `cert-manager` | ARC-001, INF-031 | [components/cert-manager.md](components/cert-manager.md) |
| Traefik | `kube-system` (local), `traefik` (gke) | ARC-001, INF-030 | [components/traefik.md](components/traefik.md) |
| Workload | `shop` | ARC-001, §6 | [components/workload.md](components/workload.md) |
