# 0011 — Agent workload identity: Keycloak federated client authentication

Status: accepted
Date: 2026-11-26

## Context

The agent authenticates to Keycloak as a client. Storing a client secret in a Kubernetes Secret would add a static client secret, which spec §3 row 0011 rules out (reason recorded there: no static client secrets), and SEC-101 requires that no secret value appears in Git, Helm values files or Terraform variables and state. Keycloak federated client authentication accepts Kubernetes service-account tokens as the client credential.

This decision is row 0011 of the ADR index in spec §3. Primary reason recorded there: No static client secrets.

## Decision

Agent workload identity: Keycloak federated client authentication with Kubernetes service-account tokens.

Spec §3 row 0011 is the source of this wording. It is implemented by requirement IDs SEC-032, SEC-033.

## Consequences

- Pods need projected service-account tokens and Keycloak must reach the cluster's issuer discovery document (SEC-032, SEC-033).
- TST-SEC-016 verifies the flow on a kind cluster.

## Alternatives considered

- Client secrets in Kubernetes Secrets: not chosen because spec §3 names "no static client secrets" as the reason.

## Spec references

SEC-032, SEC-033; spec §3 row 0011.
