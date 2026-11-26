## Project summary

Rootline is an AI SRE agent that diagnoses incidents in its own Kubernetes cluster. A Fault Lab injects
labelled faults into a trimmed OpenTelemetry Demo shop and captures replayable snapshots; a LangGraph
planner/executor agent investigates through three OAuth-protected MCP servers; a policy gate (OPA)
decides whether the agent's GitOps fix merges automatically, needs a passkey-backed approval, or is
denied; an offline eval runner turns the snapshots into a benchmark.

## Before any task

Before any task, load the `rootline-wiki` skill (or read `.claude/skills/rootline-wiki/SKILL.md`) and follow it.

- Spec: [docs/superpowers/specs/2026-11-25-rootline-design.md](docs/superpowers/specs/2026-11-25-rootline-design.md)
- Plans: [docs/superpowers/plans/](docs/superpowers/plans/) (start with `2026-11-26-rootline-00-overview.md`)
- Wiki: [wiki/index.md](wiki/index.md)

## Branch rules (spec §4.3)

- `main`: releases only, via the release PR `develop → main` titled `release: milestone <N>` (merge commit).
- `develop`: integration branch; changes arrive by squash-merged PRs.
- Work branches from `develop`: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`. Urgent release fixes: `hotfix/<slug>` from `main`, merged into `main` and `develop`.
- Never force-push `main` or `develop`. Never push directly to `main`.

## Commit rules (GEN-022)

- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, `build:`, `perf:`, `revert:`, with optional scope = component directory name, e.g. `feat(agent): add verify node`.
- Commits end with the trailer for your role in `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §7.1, "Commit attribution trailers" (implementer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, planner `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, coordinator `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`).

## Agent models and roles (owner instruction, 2026-11-26 — mandatory)

- Planning: Opus 5.5 with high effort
- Implementation: Sonnet 5.5 with high effort
- Review: Opus 5.5 with high effort
- Haiku 5.5 will coordinate the swarm of subagents

These assignments are strict. No other model or effort level may be used for these roles.

| Role | Model ID | Effort | Runs as | Responsibilities |
|---|---|---|---|---|
| Coordinator | `claude-haiku-5-5` | `medium` (Haiku 5.5's default effort; the owner set no effort for this role) | The top-level Claude Code session, started inside WSL from `/home/arkhash0309/projects/rootline` with `claude --model claude-haiku-5-5`. It is the only role that spawns subagents, because subagents cannot spawn subagents | Reads the execution schedule, dispatches planner, implementer and reviewer subagents, runs the integration gate, performs mechanical git operations (branches, merges, PRs), updates `wiki/status.md`, asks the owner for **[OWNER]** / **[CONFIRM]** / **[PAID]** steps. It does not write or review application code itself |
| Planner | `claude-opus-5-5` | `high` | Subagent `rootline-planner` (`.claude/agents/rootline-planner.md`) | Writes and amends specs, plans, the execution schedule and ADRs; decides spec gaps (spec §0.3); re-plans after a task fails 3 fix rounds; designs non-trivial merge-conflict resolutions |
| Implementer | `claude-sonnet-5-5` | `high` | Subagent `rootline-implementer` (`.claude/agents/rootline-implementer.md`); in its own git worktree when its task is in a parallel stage | Executes exactly one plan task test-first; fixes review findings, gate failures and conflicts on its own task branch |
| Reviewer | `claude-opus-5-5` | `high` | Subagent `rootline-reviewer` (`.claude/agents/rootline-reviewer.md`); read-only, may run tests | Reviews every task (spec compliance, then code quality) and every integration before it reaches `develop` |

- When dispatching with the Agent tool, the coordinator MUST pass the matching `model` and `effort` explicitly, even when the agent definition already sets them.
- If any of these models is unavailable, the coordinator stops and asks the owner. It never substitutes another model.
- These are the models that **build** Rootline. The models **inside** the Rootline product (`claude-haiku-5-5` and `claude-sonnet-5-5` per spec AGT-050) are a separate, unrelated choice.
- The full execution protocol (parallel stages, worktrees, integration gate, merge order) is in [docs/superpowers/plans/2026-11-26-rootline-00-overview.md](docs/superpowers/plans/2026-11-26-rootline-00-overview.md) §7, and the machine-readable schedule is [docs/superpowers/plans/2026-11-26-rootline-schedule.yaml](docs/superpowers/plans/2026-11-26-rootline-schedule.yaml).

The documentation rule in CLAUDE.md ("Documentation rule") applies to every document you write.
