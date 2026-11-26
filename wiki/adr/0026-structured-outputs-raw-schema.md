# 0026 — Structured outputs: raw JSON schema through messages.create

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-1 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-1 (spec reference AGT-052): The `messages.parse` helper is unavailable for Message Batches requests, so interactive and batch calls would send different schemas.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-1: Both `anthropic` and `anthropic-batch` backends send `output_config.format = {"type":"json_schema","schema": rootline_llm.schema.output_schema(Model)}` via `messages.create` (or the batch request `params`), then validate the first text block with `Model.model_validate_json`. `output_schema` copies the Pydantic JSON schema, inlines `$defs`, sets `additionalProperties: false` on every object, and removes keywords the API does not support (`minLength`, `maxLength`, `minItems` > 1, `maxItems`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `pattern`, `format` other than `date-time`/`date`). Pydantic re-checks the removed constraints and failures trigger the AGT-062 repair retry.

## Consequences

- `rootline_llm.schema.output_schema` is an own transform of the Pydantic schema and is covered by tests (W4-T01).
- Pydantic re-validation catches every constraint that the transform removes, and a failure triggers the AGT-062 repair retry.

## Alternatives considered

- Use `messages.parse` for interactive calls and a raw schema only in batch calls: not chosen because the two paths would send different schemas (PG-1).

## Spec references

PG-1, AGT-052, AGT-062; spec §26 rows PG-1; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
