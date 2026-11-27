# keycloak-config

Status: not implemented yet — planned in W3-T01.

## Purpose

keycloak-config-cli Job (ArgoCD PostSync hook) that applies realm `rootline` from `deploy/charts/rootline/files/realm/rootline.yaml` on every sync (SEC-012).

## Requirement IDs

SEC-012, SEC-020 to SEC-023a, ARC-001. Source: `docs/superpowers/specs/2026-11-25-rootline-design.md`.

## Interfaces

No network interface. Image `adorsys/keycloak-config-cli` with `import.managed.*=full` for clients, roles, client scopes, authentication flows and identity providers.

## Configuration

Realm settings: access token lifespan 300 s (client `rootline-agent` 600 s), SSO session idle 1,800 s and max 36,000 s, brute-force protection 5 failures then 60 s (SEC-012).

## Dependencies

Keycloak (admin API).

## Data owned

Realm configuration (inside the Keycloak database).

## Failure modes and handling

Realm file invalid or Keycloak unreachable: the Job fails and the previous realm stays in place.

## Runbook links

[recovery](../runbooks/recovery.md)

## Last verified

Not verified: no deployed component exists to verify. Page created 2026-11-27 in W1-T03 from the spec (base commit `f85bb63`).
