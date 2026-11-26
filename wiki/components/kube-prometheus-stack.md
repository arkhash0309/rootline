# kube-prometheus-stack

Status: not implemented yet — planned in W1-T11.

## Purpose

Prometheus, Alertmanager, kube-state-metrics and prometheus-operator, installed from the kube-prometheus-stack chart (spec §6.4, §6.5).

## Requirement IDs

WKL-021, WKL-023, WKL-030 to WKL-032, ARC-001, ARC-002, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Prometheus port 9090, Alertmanager port 9093 in namespace `observability`; Prometheus runs with `--web.enable-otlp-receiver`; alert rules: spec §6.5; Alertmanager posts to `http://api.rootline.svc/hooks/alertmanager` (spec §5.6.1).

## Configuration

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

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
