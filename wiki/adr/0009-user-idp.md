# 0009 — User identity provider: Keycloak with passkeys

Status: accepted
Date: 2026-11-26

## Context

Users need modern authentication including passkeys, and the agent needs delegated tokens through token exchange. Keycloak provides both, runs in the cluster at no cost, and is the reference implementation for the token-exchange and federated-client-authentication features that the design uses.

This decision is row 0009 of the ADR index in spec §3. Primary reason recorded there: Free; token exchange; federated client authentication.

## Decision

User IdP: Keycloak `26.8.x`, self-hosted, passkeys.

Spec §3 row 0009 is the source of this wording. It is implemented by requirement IDs SEC-010 to SEC-023a.

## Consequences

- Passkeys must be registered again after every GKE spin-up, because the realm database is recreated.
- Keycloak runs at version `26.8.x` and is configured declaratively by the keycloak-config-cli Job (SEC-012).

## Alternatives considered

- Auth0 or Okta free tier: not chosen because spec §3 requires a free, self-hosted provider with token exchange.
- Dex: not chosen because spec §3 requires the provider to offer token exchange and passkeys, which Keycloak does.

## Spec references

SEC-010 to SEC-023a; spec §3 row 0009.
