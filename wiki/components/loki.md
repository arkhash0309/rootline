# loki

Status: chart implemented in W1-T11 (`deploy/charts/observability`, version pinned in `versions.yaml`); rendered and tested, not yet deployed.

## Purpose

Loki in SingleBinary mode, the log store (spec §6.4).

## Requirement IDs

WKL-020, WKL-023, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

HTTP port 3100 in namespace `observability`; OTLP endpoint `http://loki.observability.svc:3100/otlp`; query API `/loki/api/v1/query_range`.

## Configuration

Chart values: `deploy/charts/observability/values.yaml` (key `loki`); chart `6.55.0`, application `3.6.7`. `fullnameOverride: loki` makes the Service `loki` (DNS `loki.observability.svc`), `deploymentMode: SingleBinary`, filesystem storage, TSDB schema `v13`, `auth_enabled: false`, gateway, caches and canary disabled, `compactor.retention_enabled: true`. `values-gke.yaml` sets `retention_period: 24h`; `values-ci.yaml` sets `loki.enabled: false` (Chart.yaml `condition: loki.enabled`).

Retention 48 h locally and 24 h on GKE; memory request 256 Mi, limit 512 Mi (WKL-023, ARC-030).

## Dependencies

OTel Collector (writer), local storage.

## Data owned

Log chunks with the retention above.

## Failure modes and handling

Loki down: the collector buffers then drops logs; log queries return the MCP-005 error envelope.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

2026-11-27, 908e5ed. Verified by `helm template` of the chart `deploy/charts/observability` (`tests/repo/test_observability_values.py`, 17 checks plus `helm dependency build`); the stack has not been deployed to a cluster yet (that happens in W1-T12).
