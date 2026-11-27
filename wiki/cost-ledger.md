# Cost ledger

CST-012: the owner updates this page every Monday. An agent may draft it from the ledger file `~/.local/share/rootline/llm-ledger.json`, the Anthropic Console (the owner pastes the numbers) and `gcloud billing` output. All amounts are USD.

## Caps (CST-001)

Total budget is USD 100:

| Line | Cap (USD) | Enforcement |
|---|---|---|
| LLM: development (`dev` key: interactive debugging, pilots, dev iterations) | 16 | host ledger (CST-011) |
| LLM: evaluation (`eval` key: sweeps, judge) | 48 | host ledger + EVL-063 gate |
| LLM: CI (`ci` key) | 5 | per-run cap EVL-082 + separate API key |
| LLM: in-cluster agent (`cluster` key: local and GKE demos) | 6 | `core.llm_budget` (CST-010) |
| **LLM subtotal** | **75** | **Anthropic prepaid credits** purchased in total ≤ $75 (hard cap; no auto-reload) |
| GCP | 10 | billing budget alerts (INF-004); `task gke:down` after every session |
| Buffer | 15 | owner decision only, recorded in `wiki/cost-ledger.md` |

## Weekly ledger

| Week of (Monday) | Anthropic dev | Anthropic cluster | Anthropic CI | Ledger dev/eval/ci | GCP to date | Total | Variance vs plan | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-11-30 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Week 1 (Foundations): no paid API calls and no GCP resources before the week-4 and week-7 owner steps |
