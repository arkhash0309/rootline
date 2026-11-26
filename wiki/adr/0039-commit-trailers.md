# 0039 — Commit attribution trailer per agent role (spec-gap)

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-20 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

GEN-022 says: "Commits authored by AI agents MUST end with the attribution trailer in use in the session (currently `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`)." The committed `CLAUDE.md` and `AGENTS.md` bullet "Commit rules (GEN-022)" repeats that wording.

The swarm protocol (PG-16, ADR 0035, `CLAUDE.md` "Agent models and roles") runs three models in four roles: coordinator `claude-haiku-5-5`, planner `claude-opus-5-5`, implementer `claude-sonnet-5-5`, reviewer `claude-opus-5-5`. Most commits are written by implementers, so the "currently Opus 5.5" string is wrong for them. The week-1 plan's commit examples showed the Opus trailer for implementer tasks (W1-T01 Step 9 and eight more), while W1-T16 Step 9 showed the Sonnet trailer. The W1-T01 review found the inconsistency: the W1-T01 branch commit used the Sonnet trailer, and the squash commit `4898699` on `develop` carries only the Haiku trailer. The spec does not say which trailer each role writes or what a squash commit carries.

## Decision

A commit's trailer names the model of the session that wrote the commit message. The authoritative table is overview §7.1 "Commit attribution trailers"; it decides over every wave-file commit example and over the "currently" line in `CLAUDE.md`/`AGENTS.md`.

| Role (model) | Commits it writes | Trailer block (exact) |
|---|---|---|
| Implementer (`claude-sonnet-5-5`) | every commit on task branches in every mode, on `-deferred` branches, on `fix/<stage>-integration` branches, and in the `rootline-env` / `rootline-env-e2e` repositories | `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` |
| Planner (`claude-opus-5-5`) | spec, plan, schedule and ADR commits on its `docs/<slug>` branches | `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` |
| Reviewer (`claude-opus-5-5`) | none (read-only) | none |
| Coordinator (`claude-haiku-5-5`) | lockfile and generated-file regeneration commits, `wiki/status.md` commits, revert commits, merge commits into integration branches, squash commits into `develop` | `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>` |
| Owner, without an agent | any commit; the release merge `develop → main` | no trailer |

Squash commits into `develop` keep the content authors' attribution: the squash body is every distinct `Co-Authored-By:` line of the squashed commits in first-appearance order, then the Haiku line once. Merge commits into `integration/<stage>` carry the Haiku line as their body; the merged task commits keep their own trailers. The exact `gh pr merge` commands are in overview §7.1.

The week-1 plan's implementer commit examples now show the Sonnet trailer. Commits already on `develop` or `main` (for example `4898699`) are not rewritten, because `develop` and `main` are never force-pushed (spec §4.3).

This follows spec §0.3: one rule keyed on the session's model is the simplest reading of "the trailer in use in the session" and costs nothing.

## Consequences

- `git log` on `develop` shows, for every squash commit, which models wrote the change and that the coordinator merged it.
- The texts that still say "currently Opus 5.5" (GEN-022's parenthetical in the spec, the "Commit rules (GEN-022)" bullet in `CLAUDE.md` and `AGENTS.md`, and the W1-T01 Step 7 block that produced them) stay unchanged until the owner approves an edit, because `CLAUDE.md` is owner-controlled. Until then the overview §7.1 table decides.
- `tests/repo/test_layout.py::test_agent_instruction_files` checks only that `Co-Authored-By:` appears in `CLAUDE.md` and `AGENTS.md`, so it is unaffected.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Opus 5.5 trailer on every commit, as GEN-022's parenthetical says | Misattributes every implementer and coordinator commit |
| Squash commits carry only the coordinator's Haiku trailer (as `4898699` did) | Loses the attribution of the model that wrote the change |
| Squash commits carry only the content authors' trailers | Hides that the coordinator wrote the squash message |

## Spec references

GEN-021, GEN-022, spec §4.3, PG-16, PG-20, overview Global Constraints "Commits", overview §7.1, §7.6, §7.8, `CLAUDE.md` "Agent models and roles", spec §0.3, spec §26.
