# 0037 — Swarm state directory `.swarm/` and tool outputs at the repository root (spec-gap)

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-18 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

GEN-001 fixes the repository layout and says that a new top-level directory requires an ADR. `tests/repo/test_layout.py::test_no_unexpected_top_level_entries` enforces this: it fails when the repository root contains any name outside its `ALLOWED_TOP_LEVEL` set.

The swarm protocol (PG-16, ADR 0035, overview §7) keeps its local state in `.swarm/` at the repository root of the coordinator's checkout:

| Path | Written by | Content |
|---|---|---|
| `.swarm/progress.json` | `scripts/swarm_schedule.py done <stage>` (W1-T16) | `{"done": [stage ids], "stage_bases": {stage: sha}}` |
| `.swarm/stages/<stage>.json` | coordinator at stage start (overview §7.5 step 2) | the stage base sha |
| `.swarm/gates/<stage>.json` | `scripts/integration_gate.py` (W1-T16, overview §7.7) | the gate report |
| `.swarm/worktrees/<stage>/` | `scripts/integration_gate.py` (`git worktree add`, removed after the run) | temporary checkouts of the branch and the base |

On 2026-11-26 the coordinator's checkout at `/home/arkhash0309/projects/rootline` already contained `.swarm/worktrees/`, and `uv run pytest tests/repo` on `develop` at `4898699` failed with `new top-level entries need an ADR: ['.swarm']`. The W1-T01 review found the gap. The spec does not say whether untracked runtime state at the root counts as a "top-level directory" under GEN-001.

The same test will fail for two more tools that are already in the root dev dependency group (W1-T01 Step 3): pytest-cov writes `.coverage` (and `coverage.xml` with `--cov-report=xml` in `ci.yml`, `htmlcov/` with `--cov-report=html`) to the working directory, and hypothesis writes its example database to `.hypothesis/` in the working directory.

## Decision

Untracked tool state is allowed at the repository root under exactly these five names, which are added to `ALLOWED_TOP_LEVEL` in `tests/repo/test_layout.py`:

| Name | Kind | Created by | Ignored by `.gitignore` line |
|---|---|---|---|
| `.swarm` | directory | swarm tooling and the coordinator (PG-16) | `.swarm/` (added by W1-T16 Step 7) |
| `.coverage` | file | pytest-cov | `.coverage` (already present, `# Python` block) |
| `coverage.xml` | file | pytest-cov with `--cov-report=xml` | `coverage.xml` (added by W1-T16 Step 7) |
| `htmlcov` | directory | pytest-cov with `--cov-report=html` | `htmlcov/` (already present, `# Python` block) |
| `.hypothesis` | directory | hypothesis | `.hypothesis/` (added by W1-T16 Step 7) |

Rules:

1. None of these entries is ever committed. `.gitignore` covers each of them after W1-T16 Step 7.
2. The literal set is the W1-T01 Step 1 `tests/repo/test_layout.py` block in `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`. The committed file is replaced with that block by one commit in the W1-T16 PR (W1-T16 Step 0); W1-T16 runs in the sequential stage W1-S2, so the ownership check allows the change without a schedule change.
3. GEN-001's tracked layout does not change. Any other new top-level entry, tracked or untracked, still needs its own ADR and an `ALLOWED_TOP_LEVEL` change.

This follows spec §0.3: allowing the names is simpler and cheaper than moving swarm state out of the repository, and as safe, because the entries are gitignored and hold no secrets.

## Consequences

- `uv run pytest tests/repo` passes in the coordinator's checkout while `.swarm/` exists, and after coverage or hypothesis runs.
- A stray file at the root with one of these five names is not reported by the layout test; `.gitignore` keeps it out of commits.
- Parallel worktrees (`isolation: "worktree"`) and gate worktrees under `.swarm/worktrees/<stage>/` are separate checkouts; the layout test inside them sees only that checkout's root, which has no `.swarm/` of its own.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Keep swarm state outside the repository (for example `~/.local/state/rootline/swarm/`) | Changes W1-T16's interfaces and overview §7.5–§7.9 paths; the gate's `git worktree add` targets would leave the repository; more change for no safety gain |
| Make the layout test ignore every gitignored name (`git check-ignore`) | Would also hide a gitignored secret file such as a new `.env.*` variant from the layout check; less explicit than a fixed list |
| Add only `.swarm` | `.coverage`, `coverage.xml`, `htmlcov` and `.hypothesis` would fail the same test once coverage and property tests run; fixing them one at a time costs more review rounds |

## Spec references

GEN-001, GEN-002 (root dev dependency group), TST-002 (coverage), PG-16, PG-18, overview §7.5, §7.7, W1-T01 Step 1, W1-T16 Step 0 and Step 7, spec §0.3, spec §26.
