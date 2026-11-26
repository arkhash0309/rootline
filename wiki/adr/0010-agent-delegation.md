# 0010 — Agent delegation: RFC 8693 token exchange with `azp` fallback

Status: accepted
Date: 2026-11-26

## Context

When a human starts an investigation, the agent must act on that human's behalf with a token that is bound to the audience and short-lived. RFC 8693 token exchange with the `act` claim expresses this in a standard way. Keycloak ships delegation as a preview feature, so the design contains a fallback mode.

This decision is row 0010 of the ADR index in spec §3. Primary reason recorded there: Standards-based on-behalf-of; preview risk contained.

## Decision

Agent delegation: RFC 8693 token exchange with Keycloak delegation (`act` claim, preview feature), with fallback mode `azp` (§10.5).

Spec §3 row 0010 is the source of this wording. It is implemented by requirement IDs SEC-040 to SEC-044.

## Consequences

- Preview risk is contained by the fallback mode `azp` (spec §10.5).
- The final mode is decided in W3-T03 and this ADR is updated at that time.

## Alternatives considered

- Impersonation: not chosen because the standards-based on-behalf-of flow of spec §3 (`act` claim) records that an agent acted.
- Static API keys: not chosen because they cannot carry the user identity.

## Spec references

SEC-040 to SEC-044; spec §3 row 0010.
