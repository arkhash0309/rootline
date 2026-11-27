# 0020 — Embeddings: fastembed with BAAI/bge-small-en-v1.5

Status: accepted
Date: 2026-11-26

## Context

Incident memory needs text embeddings with USD 0 cost and CPU-only execution. `fastembed` runs the model `BAAI/bge-small-en-v1.5` locally and produces 384-dimension vectors.

This decision is row 0020 of the ADR index in spec §3. Primary reason recorded there: USD 0; CPU-friendly.

## Decision

Embeddings: Local `fastembed` with `BAAI/bge-small-en-v1.5` (384 dimensions).

Spec §3 row 0020 is the source of this wording. It is implemented by requirement IDs AGT-090.

## Consequences

- Vector columns have 384 dimensions.
- `fastembed` runs on CPU only, so no GPU is needed (NG5).

## Alternatives considered

- Voyage embeddings: not chosen because spec §3 requires USD 0 and CPU-friendly embeddings.
- OpenAI embeddings: not chosen for the same reason.

## Spec references

AGT-090; spec §3 row 0020.
