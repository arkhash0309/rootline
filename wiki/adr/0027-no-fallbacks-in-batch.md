# 0027 — No server-side fallbacks in batch requests

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-2 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-2 (spec reference AGT-052): Server-side `fallbacks` is rejected by the Batches API.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-2: `anthropic-batch` omits `betas`/`fallbacks`. A `refusal` result in a batch is retried once in the next flush, then raises `LLMRefusal`.

## Consequences

- A batch refusal is retried once in the next flush, then fails with `LLMRefusal`.
- Interactive calls keep the server-side fallbacks of AGT-052.

## Alternatives considered

- A client-side fallback middleware for batch requests: not chosen because it is more code than omitting `fallbacks` (spec §0.3: simplest first).

## Spec references

PG-2; spec §26 rows PG-2; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
