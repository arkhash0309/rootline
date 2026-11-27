# keycloak

Status: not implemented yet — planned in W3-T01.

## Purpose

Keycloak 26.8.x identity provider for users (passkeys) and agents (federated client authentication, token exchange) (spec §10).

## Requirement IDs

SEC-010 to SEC-012, SEC-020 to SEC-023a, SEC-030 to SEC-033, SEC-040 to SEC-044. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

Port 8080 and management port 9000 in namespace `keycloak`; public host `auth.D`; realm `rootline` (SEC-012).

## Configuration

`KC_DB=postgres`, `KC_HOSTNAME=https://auth.D`, `KC_HTTP_ENABLED=true`, `KC_PROXY_HEADERS=xforwarded`, `KC_HEALTH_ENABLED=true`, `KC_METRICS_ENABLED=true`, `JAVA_OPTS_KC_HEAP=-Xms256m -Xmx512m`; memory request 640 Mi, limit 900 Mi (SEC-010, ARC-030). The preview feature name for delegation is recorded here and in ADR 0010 in W3-T01.

## Dependencies

Postgres database `keycloak`, Traefik (TLS termination), CoreDNS custom rewrite for `auth.D` (SEC-011).

## Data owned

Database `keycloak` (owner role `keycloak`).

## Failure modes and handling

Postgres unreachable: Keycloak is not ready and no login or token request succeeds. Break-glass for a lockout: the recovery runbook.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
