# 0005 — LLM access layer: in-house `rootline-llm`

Status: accepted
Date: 2026-11-26

## Context

The agent needs Claude features that gateway libraries expose late or not at all: effort, prompt caching, structured outputs, Message Batches and server-side fallbacks. An external gateway also adds a service to a cluster that has a 9.5 GiB memory budget. Spec non-goal NG11 forbids a general-purpose LLM gateway service.

This decision is row 0005 of the ADR index in spec §3. Primary reason recorded there: Full access to Claude features (effort, caching, structured outputs, batches, server-side fallbacks); one fewer service.

## Decision

LLM access layer: In-house Python library `rootline-llm` using the official Anthropic SDK and the Ollama HTTP API. No LiteLLM.

Spec §3 row 0005 is the source of this wording. It is implemented by requirement IDs AGT-060 to AGT-066, C1.

## Consequences

- Rootline owns retries, budgets and batch handling in `rootline_llm` (spec §9.6).
- No other module imports `anthropic` or calls Ollama (AGT-004).

## Alternatives considered

- LiteLLM proxy: not chosen because it adds a service and spec §3 requires full access to Claude features without one.
- LangChain chat models: not chosen because spec §3 requires full access to Claude features (effort, caching, structured outputs, batches, server-side fallbacks) through the official SDK.

## Spec references

AGT-060 to AGT-066, C1; spec §3 row 0005.
