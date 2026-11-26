# 0003 — Workload: trimmed OpenTelemetry Demo

Status: accepted
Date: 2026-11-26

## Context

The agent needs a realistic multi-service system to diagnose, with telemetry (metrics, logs, traces), switchable faults and a public reference for comparison. The OpenTelemetry Demo ships built-in feature flags that act as fault switches and emits rich telemetry for every service. ITBench uses the same family of applications, which makes results comparable (spec §15.13).

This decision is row 0003 of the ADR index in spec §3. Primary reason recorded there: Built-in fault flags, rich telemetry, comparability with ITBench.

## Decision

Workload: OpenTelemetry Demo, Helm chart `0.42.8`, app `3.1.0`, trimmed (§6.2).

Spec §3 row 0003 is the source of this wording. It is implemented by requirement IDs WKL-001 to WKL-011.

## Consequences

- The Helm chart `open-telemetry/opentelemetry-demo` is pinned to version `0.42.8` (app `3.1.0`).
- The workload is trimmed to the components in WKL-002 and WKL-003 to fit the 9.5 GiB memory budget (S2), and rendered once to plain YAML (ADR 0017).

## Alternatives considered

- Online Boutique: not chosen because it lacks the built-in fault flags, telemetry richness and ITBench comparability that spec §3 names as the reason.
- Custom microservices: not chosen because writing and maintaining a workload costs effort and gives no built-in fault flags or ITBench comparability.

## Spec references

WKL-001 to WKL-011; spec §3 row 0003.
