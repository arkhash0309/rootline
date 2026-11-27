# telemetry

Status: not implemented yet — planned in W1-T13.

## Purpose

Records the metric and label names actually produced by the telemetry pipeline, so that the metric mapping in spec §6.5 is expressed in real names (WKL-022).

## Requirement IDs

WKL-020 to WKL-023, WKL-030 to WKL-032, OBS-001, OBS-002. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Platform metrics of OBS-002 (names fixed); Tempo metrics-generator output names are recorded here in W1-T13.

## Configuration

Retention: Prometheus 2 d, Loki 48 h, Tempo 48 h locally; 1 d, 24 h, 24 h on GKE (WKL-023).

## Dependencies

OTel Collector, Prometheus, Loki, Tempo.

## Data owned

None; the page documents names only.

## Failure modes and handling

A name in spec §6.5 does not exist in the running stack: W1-T13 records the actual name here and in the alert rules.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
