# 0015 — Database: Postgres 16 with pgvector via CloudNativePG, in cluster

Status: accepted
Date: 2026-11-26

## Context

The platform needs a relational store for incidents, audit log, lab and eval data, and a vector store for incident memory. Running Postgres in the cluster through CloudNativePG avoids a managed-database bill, and the CNPG image bundles pgvector.

This decision is row 0015 of the ADR index in spec §3. Primary reason recorded there: No managed-DB bill.

## Decision

Database: Postgres 16 + pgvector via CloudNativePG, in cluster.

Spec §3 row 0015 is the source of this wording. It is implemented by requirement IDs DB-001.

## Consequences

- Backups are disabled in every environment; persistent data is reproducible from snapshots and seed dumps (spec §16.7).
- The cluster `rootline-pg` runs in namespace `rootline-data` with one instance (DB-001).

## Alternatives considered

- Cloud SQL: not chosen because of the managed-database bill (spec §3 reason).
- SQLite: not chosen because it cannot provide the per-role grants of DB-002 and the vector extension.

## Spec references

DB-001; spec §3 row 0015.
