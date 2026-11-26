# CLAUDE.md — Rootline

Instructions for every AI coding agent working in this repository. These rules override default agent behaviour.

Project: **Rootline**, an AI SRE agent that diagnoses incidents in its own Kubernetes cluster.
Source of truth: [docs/superpowers/specs/2026-11-25-rootline-design.md](docs/superpowers/specs/2026-11-25-rootline-design.md) (SPEC-ROOTLINE-001).

## Development environment (owner instruction, 2026-11-26 — mandatory)

All development happens inside **WSL 2**, distribution `Ubuntu` (Ubuntu 26.04 LTS, systemd on), because it uses the CPU cores better (spec GEN-040, GEN-041, plan decision PG-17).

- Work only in the checkout at `/home/arkhash0309/projects/rootline` (and `/home/arkhash0309/projects/rootline-env`) on the WSL filesystem. Never work on a checkout under `/mnt/c`.
- Start every Claude Code session — the coordinator and any manual session — from a WSL shell in that directory. Subagents and their worktrees therefore run in WSL too.
- Run every project command (`task`, `uv`, `git`, `docker`, `k3d`, `kubectl`, `helm`, `terraform`, `gcloud`, `gh`, `ollama`) in WSL bash. Never use PowerShell, cmd or Git Bash for project commands.
- Docker is the native Docker Engine inside WSL (systemd service `docker`); Docker Desktop is not used.
- Windows is used only for the browser (console, Keycloak, ArgoCD, passkeys with Windows Hello) and for `%UserProfile%\.wslconfig` (`memory=12GB`, `processors=16`, `swap=8GB`, `localhostForwarding=true`). Open URLs from WSL with `wslview <url>`.

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

## Documentation rule: every document must be detailed and unambiguous

All implementation in this project is done by AI coding agents. Any gap or vague statement in a document will be filled with a guess, so every document must leave **nothing open to interpretation**. Length does not matter: a document can run to thousands of lines.

### Scope

This rule applies to every document an agent writes or edits in this repository, including:

| Document type | Location |
|---|---|
| Design specs | `docs/superpowers/specs/` |
| Implementation plans | `docs/superpowers/plans/` |
| Wiki pages | `wiki/` |
| Architecture Decision Records (ADRs) | `wiki/adr/` |
| Runbooks | `wiki/runbooks/` |
| READMEs, `CLAUDE.md`, `AGENTS.md` and other files aimed at agents | anywhere in the repo |
| Code comments and docstrings that describe behaviour, contracts or invariants | source files |

It does not apply to commit messages or PR descriptions, though those should still be specific.

### Requirements

A document complies with this rule only if all of the following hold:

1. **Exact values are pinned.** Write the literal value, never a placeholder or a range. This covers versions, defaults, thresholds, limits, timeouts, names, file paths, ports, environment variable names, error codes, model IDs and prices.
   - Wrong: "use a recent version of Keycloak", "a short timeout".
   - Right: "Keycloak `26.8.0`", "timeout `30 s`".
2. **Every open choice is resolved.** If the document presents options, it states which one is chosen. If a choice must be made at run time, it gives the decision rule *and* the default that applies when the rule does not decide.
3. **Interfaces are fully specified.** For every API endpoint, MCP tool, function, CLI command, queue message, database table or config file, the document defines inputs (names, types, required/optional, constraints), outputs (shape and types), errors (codes and when each occurs) and side effects. Naming a component without its interface does not comply.
4. **Terms are defined.** Every project-specific term is defined in the document or links to its definition (the spec's glossary, §2).
5. **No vague words.** These words and phrases are forbidden unless immediately followed by the concrete meaning: "etc.", "and so on", "as needed", "appropriate", "reasonable", "where applicable", "if necessary", "some", "various", "TBD", "TODO", "later".
6. **Requirements carry IDs.** Normative statements carry a stable ID of the form `<AREA>-<NNN>`, using the area prefixes in the spec's §0.2 (for example `EVL-040`, `SEC-021`), so plans, tests and code comments can reference them. Implementation plans cite these IDs in task descriptions; tests cite them in docstrings. Normative language follows the spec's §0.1: **MUST**, **MUST NOT**, **SHOULD**, **MAY**.
7. **Tables over prose for structured facts.** Catalogues, mappings, settings, budgets and comparisons are written as tables.
8. **Examples are concrete.** Where an example helps, give a complete, valid one (a full JSON payload, a full command line), not a fragment with `...`.
9. **Failure behaviour is stated.** For every operation, the document says what happens on timeout, invalid input, missing dependency and partial failure.
10. **Cross-references are exact.** Refer to other material by requirement ID, section number and file path, never by "see above" or "the relevant section".

### When the source material is ambiguous

If an agent finds that the spec or another document does not answer a question it needs answered:

1. Do not guess silently. Choosing without recording is a defect.
2. If the decision changes cost, security, scope or anything the owner has already approved, stop and ask the owner before proceeding.
3. Otherwise, follow the spec's §0.3: pick the option that is simplest, cheapest and safest, in that priority order.
4. Record the decision as an ADR in `wiki/adr/` (spec §21.3) in the same pull request, with the label `spec-gap`.
5. Add the question and the decision to the spec's gap log (§26) in that same pull request.

### Self-check before finishing a document

Before declaring a document done, the agent re-reads it and confirms:

- [ ] Every value an implementer needs is written down literally.
- [ ] No forbidden vague word from requirement 5 remains.
- [ ] Every interface has inputs, outputs, errors and side effects.
- [ ] Every cross-reference resolves to an existing ID, section or file.
- [ ] No two statements contradict each other.
- [ ] Someone with no access to the conversation that produced the document could implement from it without asking a question.
