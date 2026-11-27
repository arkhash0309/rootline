# 0033 — Workload render refinements for flagd and OTLP endpoints

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-11, PG-12 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-11 (spec reference WKL-010 step 6, LAB-020): Chart 0.42.8 copies `flagd-config` into an `emptyDir` with init container `init-config`, so a live ConfigMap patch never reaches flagd.

PG-12 (spec reference WKL-010 step 5): Containers use both OTLP gRPC (`:4317`) and OTLP HTTP (`:4318`) through `http://$(OTEL_COLLECTOR_NAME):<port>`; forcing every endpoint to `:4317` breaks HTTP exporters.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-11: The render script removes init container `init-config` and sidecar `flagd-ui`, and mounts ConfigMap `flagd-config` read-only at `/etc/flagd` in place of the `config-rw` emptyDir. The flagd command stays `--uri file:./etc/flagd/demo.flagd.json`. W2-T08 measures the reload; if flagd does not serve the new variant within 120 s of the patch, the flag injector also deletes the flagd pod after patching (fallback recorded in the ADR and in `wiki/components/workload.md`).

PG-12: The render script sets `OTEL_COLLECTOR_NAME=otel-collector.observability.svc.cluster.local` wherever the variable exists and leaves each endpoint's scheme and port unchanged. Containers whose endpoint does not use `$(OTEL_COLLECTOR_NAME)` get their host replaced by the same FQDN, keeping the port.

## Consequences

- Live flag drift is possible because flagd reads the mounted ConfigMap; W2-T08 measures the reload and records the fallback (deleting the flagd pod) if flagd does not serve the new variant within 120 s.
- The collector is addressed by its FQDN `otel-collector.observability.svc.cluster.local` through `OTEL_COLLECTOR_NAME`.

## Alternatives considered

- Keep the init-copy of the flag ConfigMap and always restart flagd after a patch: not chosen because a live ConfigMap patch never reaches flagd through the init-copy (PG-11).
- Force every OTLP endpoint to port 4317: not chosen because it breaks HTTP exporters (PG-12).

## Spec references

PG-11, PG-12, WKL-010, LAB-020; spec §26 rows PG-11, PG-12; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
