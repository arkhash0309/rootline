# loki

Status: not implemented yet — planned in W1-T11.

## Purpose

Loki in SingleBinary mode, the log store (spec §6.4).

## Requirement IDs

WKL-020, WKL-023, ARC-001, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

HTTP port 3100 in namespace `observability`; OTLP endpoint `http://loki.observability.svc:3100/otlp`; query API `/loki/api/v1/query_range`.

## Configuration

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

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
