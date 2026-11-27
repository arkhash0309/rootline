# 0014 — Job queue: Postgres with FOR UPDATE SKIP LOCKED

Status: accepted
Date: 2026-11-26

## Context

Investigations are queued and claimed by two agent workers. A Postgres table with `FOR UPDATE SKIP LOCKED` guarantees that one worker holds a job at a time, with leases, and needs no additional service, which matters for the 9.5 GiB budget.

This decision is row 0014 of the ADR index in spec §3. Primary reason recorded there: Avoids Redis and Kafka.

## Decision

Job queue: Postgres table with `FOR UPDATE SKIP LOCKED`.

Spec §3 row 0014 is the source of this wording. It is implemented by requirement IDs AGT-030.

## Consequences

- The agent contains lease and reaper code (AGT-030).
- The role `rootline_agent` may update only the columns of `core.jobs` listed in DB-002.

## Alternatives considered

- Redis with RQ: not chosen because spec §3 avoids adding Redis or Kafka.
- Kafka: not chosen for the same reason.

## Spec references

AGT-030; spec §3 row 0014.
