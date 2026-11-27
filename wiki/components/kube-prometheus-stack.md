# kube-prometheus-stack

Status: chart implemented in W1-T11 (`deploy/charts/observability`, version pinned in `versions.yaml`); rendered and tested, not yet deployed.

## Purpose

Prometheus, Alertmanager, kube-state-metrics and prometheus-operator, installed from the kube-prometheus-stack chart (spec §6.4, §6.5).

## Requirement IDs

WKL-021, WKL-023, WKL-030 to WKL-032, ARC-001, ARC-002, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Prometheus port 9090, Alertmanager port 9093 in namespace `observability`; Prometheus runs with `--web.enable-otlp-receiver`; alert rules: spec §6.5; Alertmanager posts to `http://api.rootline.svc/hooks/alertmanager` (spec §5.6.1).

## Configuration

Chart values: `deploy/charts/observability/values.yaml` (key `kube-prometheus-stack`), overrides in `values-gke.yaml` (retention `1d`) and `values-ci.yaml` (retention `6h`; Loki, Tempo and the collector disabled). Chart `94.1.0`, application `0.95.2`. Set in `values.yaml`: `prometheusSpec.enableOTLPReceiver: true`, `prometheusSpec.otlp.promoteResourceAttributes` = `service.name`, `k8s.namespace.name`, `k8s.pod.name`, `k8s.deployment.name`, `enableRemoteWriteReceiver: true` (Tempo metrics-generator), selector-nil flags `false` for ServiceMonitor, PodMonitor and rules, `grafana.enabled: false`, `nodeExporter.enabled: false`, `crds.enabled: false` (CRDs come from the `prometheus-crds` Application), `defaultRules.create: false`. `kubeControllerManager`, `kubeEtcd`, `kubeScheduler` and `kubeProxy` are `enabled: false` (ADR 0046 O5): on k3s these components listen on `127.0.0.1` only and on GKE they are managed, so their targets would always be down. ServiceMonitors `kubelet`, `apiserver`, `coredns`, `kube-state-metrics`, `operator`, `prometheus` and `alertmanager` stay.

NetworkPolicies (`templates/networkpolicies.yaml`, namespace `observability`, ADR 0046 O4): `allow-same-namespace`, `allow-otlp-ingress` (only the collector pods, labels `app.kubernetes.io/name: opentelemetry-collector` and `component: agent-collector`; 4317, 4318 from every namespace), `allow-query-ingress` (9090, 3100, 3200 from `rootline` and `observability`), `allow-alertmanager-ingress` (9093 from `observability`), `allow-operator-webhook-ingress` (only the operator pods; 10250 from any address, the kube-apiserver calls the admission webhook), `allow-egress-pods` (all namespaces), `allow-egress-apiserver` (TCP 443, 6443 to any address) and `allow-egress-kubelet` (only pods labelled `app.kubernetes.io/name: prometheus`; TCP 10250 to any address; no other policy allows egress 10250). The Prometheus pod label is unverified until W1-T12 Step 5. The optional `debug.grafana` flag of ARC-002 is not implemented (it is a MAY).

Scrape interval 15 s; retention 2 d locally and 1 d on GKE; Grafana is not deployed (ARC-002). Memory requests: Prometheus 768 Mi, Alertmanager 48 Mi, operator 96 Mi, kube-state-metrics 64 Mi (ARC-030).

## Dependencies

OTel Collector (OTLP metrics), Tempo metrics-generator (remote write), `api` webhook.

## Data owned

TSDB with the retention above.

## Failure modes and handling

Prometheus down: no alerts fire and no metrics are available to `mcp-telemetry`. Webhook target down: Alertmanager retries delivery.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed. Verified by `helm template` of the chart `deploy/charts/observability` (`tests/repo/test_observability_values.py`, 24 checks plus `helm dependency build`); the stack has not been deployed to a cluster yet (that happens in W1-T12).
