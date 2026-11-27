# console

Status: not implemented yet — planned in W6-T01.

## Purpose

Next.js 16 user interface and backend-for-frontend (BFF) for Rootline. The BFF holds the user session and calls `api` with the user's access token (spec §14, §5.6.2).

## Requirement IDs

UI-001 to UI-005, UI-010, UI-020, UI-030, UI-040, UI-050 to UI-052, ARC-001, ARC-020, ARC-030. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Routes and pages: spec §14.3. BFF: spec §14.2. Container port 3000 behind Service port 80, DNS `console.rootline.svc.cluster.local`; public host `console.D` through Traefik (INF-040).

## Configuration

Memory request 192 Mi, limit 384 Mi, 1 replica locally and on GKE (ARC-001, ARC-030). Environment variables are defined in W6-T01.

## Dependencies

`api` (HTTP, user token), Keycloak (OIDC login, passkeys), Postgres schema `bff` through role `rootline_console` (DB-002).

## Data owned

Schema `bff`, table `bff.sessions` (DB-002, spec §13.6).

## Failure modes and handling

`api` unreachable: BFF requests fail and the page shows the error state of spec §14.7. Postgres unreachable: sessions cannot be read or written, so login fails (role grants in DB-002). Keycloak unreachable: login fails.

## Runbook links

[local-up](../runbooks/local-up.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
