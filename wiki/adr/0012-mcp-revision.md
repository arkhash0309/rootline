# 0012 — MCP revision 2026-07-28 with streamable HTTP

Status: accepted
Date: 2026-11-26

## Context

The three MCP servers are OAuth 2.0 resource servers. Revision `2026-07-28` of the MCP specification is the current revision and makes protected-resource metadata mandatory, which the authorization design depends on (SEC-051).

This decision is row 0012 of the ADR index in spec §3. Primary reason recorded there: Current revision with mandatory protected-resource metadata.

## Decision

MCP revision: MCP specification revision `2026-07-28`, streamable HTTP transport.

Spec §3 row 0012 is the source of this wording. It is implemented by requirement IDs MCP-001, SEC-051, SEC-052.

## Consequences

- The pinned `mcp` SDK `2.3.0` (`versions.yaml`) implements revision `2026-07-28`, and `versions.yaml` sets no `mcp_protocol_revision` fallback key, so no fallback is used and no deviation between the spec text and the SDK is recorded (MCP-001, SEC-052).

## Alternatives considered

- Revision 2025-11-25: not chosen because spec §3 names the current revision with mandatory protected-resource metadata as the reason.

## Spec references

MCP-001, SEC-051, SEC-052; spec §3 row 0012.
