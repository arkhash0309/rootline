# 0042 — W1-T05 baseline and verification without the `writing-skills` skill (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-23 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

Plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`, "Task W1-T05" (`rootline-wiki` agent skill, WIK-030), has two coordinator steps that name the superpowers `writing-skills` skill:

| Step | Schedule role (`docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`, stage `W1-P2`) | Text before this ADR |
|---|---|---|
| Step 1 | `pre_steps: [1]` (overview §7.3, §7.5 step 1) | "Load the superpowers `writing-skills` skill and follow its process"; the coordinator dispatches a fresh `rootline-implementer` (Sonnet 5.5, high) as the test subject, with the scenario "implement a one-line change in `libs/py-common` and finish the task", records whether the agent updated `wiki/log.md` and ran `task wiki:lint`, and passes the recorded baseline to the W1-T05 implementer |
| Step 4 | `deferred_steps: [4]`, `deferred_to: W1-S3` | "Verify with the writing-skills process": re-run the baseline scenario with the skill loaded; the agent must update `wiki/log.md` and run `task wiki:lint`; record the result in `wiki/log.md` |

On 2026-11-27, when the coordinator prepared stage `W1-P2` (`origin/develop` was at `ae2b199`), the `writing-skills` skill was not in the coordinator session's skill list, so Step 1 cannot run as written. The coordinator is Haiku 5.5 (`CLAUDE.md` "Agent models and roles") and must not reconstruct the content of a skill it cannot load. No document defines that process, the exact fields of the baseline record, where the record is stored, how the coordinator determines that the subject "ran `task wiki:lint`", or what happens when the baseline already shows the wanted behaviour or when the baseline run itself fails.

Facts checked on `ae2b199` on 2026-11-27:

| Fact | Evidence |
|---|---|
| `.claude/skills/rootline-wiki/` contains only `.gitkeep`; `SKILL.md` does not exist | `ls -la .claude/skills/rootline-wiki` |
| `Taskfile.yml` does not exist; W1-T06 creates it in the same stage `W1-P2` (task `wiki:lint` in the W1-T06 Taskfile block) | repository root listing; W1 plan "Task W1-T06" |
| `scripts/wiki_lint.py` exists (W1-T03, merged in `W1-P1`) | `scripts/wiki_lint.py` |
| `libs/py-common/rootline_common/__init__.py` has exactly two non-empty lines: the module docstring and `__version__ = "0.1.0"`; W1-T07 "Files" creates other modules and does not modify `__init__.py` | file content; W1 plan "Task W1-T07" |
| `scripts/integration_gate.py` writes only `.swarm/gates/<stage>.json` (stage IDs have the form `W<n>-S<n>` or `W<n>-P<n>`); no script reads other files in `.swarm/gates/` | `scripts/integration_gate.py` line 916; `grep -rn gates scripts/` |
| The `rootline-implementer` definition rule 1 reads `.claude/skills/rootline-wiki/SKILL.md` "once it exists" and rule 7 runs `uv run python scripts/wiki_lint.py` "once it exists" | `.claude/agents/rootline-implementer.md` |

## Decision

Spec §0.3 applies: simplest, cheapest, safest, in that order. The decision changes no cost (one extra Sonnet 5.5 subagent run per step, which the plan already required), no security posture and no scope.

### D1. The `writing-skills` process is replaced

1. Step 1 and Step 4 of W1-T05 do not load or reference the `writing-skills` skill. Its process is replaced by three checks that the plan and this ADR fully define:
   - **Behaviour before the skill (Step 1):** the baseline run of D2 to D4, recorded in `.swarm/gates/W1-T05-baseline.json`.
   - **Red-green test (Steps 2 and 5):** `uv run pytest tests/repo/test_skill.py -v` fails before `SKILL.md` exists (Step 2) and passes after the Step 3 text is written (Step 5). The W1-T05 implementer runs both, unchanged from the plan.
   - **Behaviour with the skill (Step 4):** the verification run of D6, the same scenario with `SKILL.md` present, recorded in `.swarm/gates/W1-T05-verify.json` and summarised in `wiki/log.md`.
2. The text of `SKILL.md` stays exactly the W1-T05 Step 3 block. The baseline result does not change it.

### D2. Scenario run (used by Step 1 and by Step 4)

The coordinator runs a scenario run as follows. `<kind>` is `baseline` (Step 1) or `verify` (Step 4); `<n>` is the attempt number, `1` or `2`.

1. **Base.** Step 1: the `W1-P2` stage base recorded in `.swarm/stages/W1-P2.json` (overview §7.5 step 2). Step 4: the `origin/develop` tip when stage `W1-S3` starts, before any W1-S3 task is dispatched (overview §7.3, deferred steps run first).
2. **Precondition.** In a checkout of the base, `grep -qxF '__version__ = "0.1.0"' libs/py-common/rootline_common/__init__.py` exits 0. If it exits non-zero, the coordinator does not dispatch the subject, writes the record with `result: "BLOCKED"` and one attempt object with `attempt: 1`, `subject_status: "NOT_DISPATCHED"`, every boolean `false`, `changed_files: []`, `commands_reported: []` and `failure_reason: "precondition: __version__ line missing at base"`, and follows D5 step 3 (the stage stops for the owner and the planner). A failed precondition is not retried.
3. **Dispatch.** One Agent call: `subagent_type: "rootline-implementer"`, `model: "sonnet"`, `effort: "high"`, `isolation: "worktree"`, description `W1-T05 <kind> subject a<n>`, prompt exactly the text below with `<kind>`, `<n>` and `<base sha>` (40 hex characters) substituted. Every subject is a fresh agent; a subject is never continued with SendMessage.

   ```text
   You are the test subject of a scenario run. This run is not a plan task: there is no plan_file, no schedule entry and no stage. Skip the check_ownership.py command of your rule 7 (it would exit 2 for an unknown task). Do not push any branch and do not open a pull request; this overrides your rule 8. Everything else in your agent definition applies.

   task_id: none
   plan_file: none
   branch: feat/w1-t05-<kind>-a<n>
   base: <base sha>
   stage: none
   mode: implement
   details: Implement a one-line change in libs/py-common and finish the task. The change: in libs/py-common/rootline_common/__init__.py replace the line `__version__ = "0.1.0"` with `__version__: str = "0.1.0"`. Create the branch from base, make the change, and commit it.

   After your normal report, add exactly two more lines:
   WORKTREE: <absolute path of the git worktree you worked in>
   COMMANDS: <every shell command you ran, in the order you ran them, separated by " ;; ">
   ```

   The prompt names neither the wiki, nor `task wiki:lint`, nor this ADR, so the run measures the subject's unprompted behaviour. The two extra report lines are the same in both kinds of run, so the comparison between baseline and verification is fair.
4. **Time limit.** If the Agent call has not returned 60 minutes after dispatch, the coordinator stops it (TaskStop) and the attempt has `subject_status: "TIMEOUT"`.
5. **Inspection.** After the subject returns (or is stopped), the coordinator computes the record fields of D3 with these commands, run from `/home/arkhash0309/projects/rootline` (`<wt>` is the `WORKTREE:` path; when that line is missing or the path does not exist, `<wt>` is the worktree path in the Agent call's result; when neither exists, the working-tree checks count as no change):

   | Field | Command | Value |
   |---|---|---|
   | `skill_present` | `git cat-file -e <base sha>:.claude/skills/rootline-wiki/SKILL.md` | `true` if exit 0, else `false` |
   | committed paths | `git diff --name-only --no-renames <base sha> feat/w1-t05-<kind>-a<n>` (no output when the branch does not exist) | list of paths |
   | uncommitted paths | `git -C <wt> status --porcelain=v1 --untracked-files=all`, path = characters from column 4 to end of line | list of paths |
   | `scenario_change_committed` | `git show feat/w1-t05-<kind>-a<n>:libs/py-common/rootline_common/__init__.py \| grep -qxF '__version__: str = "0.1.0"'` | `true` if exit 0, else `false` |
   | `log_md_updated` | `wiki/log.md` is in committed paths or in uncommitted paths | `true` / `false` |
   | `ran_task_wiki_lint` | at least one entry of `COMMANDS:` (split on ` ;; `), after removing a leading `cd <dir> && `, has first word `task` and contains the word `wiki:lint` | `true` / `false` |
   | `ran_wiki_lint_script` | at least one entry of `COMMANDS:` contains `scripts/wiki_lint.py` | `true` / `false` |
   | `pushed` | `git ls-remote --heads origin feat/w1-t05-<kind>-a<n>` prints a line | `true` / `false` |

   `ran_task_wiki_lint` counts the invocation whatever its exit code: at the Step 1 base, `Taskfile.yml` does not exist, so `task wiki:lint` fails there even when the subject runs it.
6. **Clean-up.** After the record is written: if `pushed` is `true`, `git push origin --delete feat/w1-t05-<kind>-a<n>`; then `git worktree remove --force <wt>` (when `<wt>` exists) and `git branch -D feat/w1-t05-<kind>-a<n>` (when the branch exists). Nothing from a scenario run is merged, reviewed or committed to any shared branch.

### D3. Record file

The coordinator writes the record with the Write tool, as UTF-8 JSON with two-space indentation and a final newline, to:

| Step | Path |
|---|---|
| Step 1 | `/home/arkhash0309/projects/rootline/.swarm/gates/W1-T05-baseline.json` |
| Step 4 | `/home/arkhash0309/projects/rootline/.swarm/gates/W1-T05-verify.json` |

`.swarm/` is ignored by git and never committed (ADR 0037). The names cannot collide with gate reports, which are named after stage IDs.

Top-level object:

| Field | Type | Value |
|---|---|---|
| `record` | string | `"W1-T05-baseline"` or `"W1-T05-verify"` |
| `adr` | string | `"0042"` |
| `base_sha` | string | the 40-hex base of D2 step 1 |
| `result` | string | one of the values in the `result` table below |
| `attempts` | array of attempt objects | one object per attempt, in order, at most 2 |

Attempt object:

| Field | Type | Value |
|---|---|---|
| `attempt` | integer | `1` or `2` |
| `recorded_at` | string | UTC time the attempt was inspected, format `YYYY-MM-DDTHH:MM:SSZ` |
| `branch` | string | `feat/w1-t05-<kind>-a<n>` |
| `subject_agent` | string | `"rootline-implementer"` |
| `subject_model` | string | `"claude-sonnet-5-5"` |
| `subject_effort` | string | `"high"` |
| `subject_status` | string | the `STATUS:` value of the subject's report (`"DONE"`, `"BLOCKED"`, `"FAILED"`); `"NO_REPORT"` when the report has no `STATUS:` line; `"TIMEOUT"` (D2 step 4); `"AGENT_ERROR"` when the Agent call returned an error; `"NOT_DISPATCHED"` when the D2 step 2 precondition failed |
| `skill_present` | boolean | D2 step 5 |
| `scenario_change_committed` | boolean | D2 step 5 |
| `log_md_updated` | boolean | D2 step 5 |
| `ran_task_wiki_lint` | boolean | D2 step 5 |
| `ran_wiki_lint_script` | boolean | D2 step 5 |
| `pushed` | boolean | D2 step 5 |
| `changed_files` | array of strings | union of committed and uncommitted paths, sorted, no duplicates |
| `commands_reported` | array of strings | the `COMMANDS:` entries in order; `[]` when the line is missing |
| `failure_reason` | string or null | `null` for a valid attempt (D4); `"precondition: __version__ line missing at base"` when the D2 step 2 precondition failed; otherwise the first failing condition of D4, written as in that table |

`result` values:

| Value | When |
|---|---|
| `"baseline-fails"` | Step 1, the valid attempt has `log_md_updated: false` or `ran_task_wiki_lint: false` (the skill is needed; the expected case) |
| `"baseline-passes"` | Step 1, the valid attempt has `log_md_updated: true` and `ran_task_wiki_lint: true` |
| `"verify-passes"` | Step 4, the valid attempt has `skill_present: true`, `log_md_updated: true` and `ran_task_wiki_lint: true` |
| `"verify-fails"` | Step 4, the valid attempt has `skill_present: false`, `log_md_updated: false` or `ran_task_wiki_lint: false` |
| `"BLOCKED"` | both attempts are invalid (D5), or the D2 step 2 precondition failed |

Complete example of a Step 1 record (one valid attempt):

```json
{
  "record": "W1-T05-baseline",
  "adr": "0042",
  "base_sha": "ae2b19916582233f4a1a1afe722ec054ee48f1b3",
  "result": "baseline-fails",
  "attempts": [
    {
      "attempt": 1,
      "recorded_at": "2026-11-27T11:42:05Z",
      "branch": "feat/w1-t05-baseline-a1",
      "subject_agent": "rootline-implementer",
      "subject_model": "claude-sonnet-5-5",
      "subject_effort": "high",
      "subject_status": "DONE",
      "skill_present": false,
      "scenario_change_committed": true,
      "log_md_updated": false,
      "ran_task_wiki_lint": false,
      "ran_wiki_lint_script": true,
      "pushed": false,
      "changed_files": [
        "libs/py-common/rootline_common/__init__.py"
      ],
      "commands_reported": [
        "git switch -c feat/w1-t05-baseline-a1 ae2b19916582233f4a1a1afe722ec054ee48f1b3",
        "uv run ruff check libs/py-common",
        "uv run mypy libs/py-common",
        "uv run python scripts/wiki_lint.py",
        "git commit -am \"refactor(py-common): annotate __version__\""
      ],
      "failure_reason": null
    }
  ]
}
```

### D4. Valid attempt

An attempt is valid when every condition below holds. The first condition that does not hold, in table order, is its `failure_reason`.

| Order | Condition | `failure_reason` text when it does not hold |
|---|---|---|
| 1 | `subject_status` is `"DONE"` | `subject_status <value>` |
| 2 | The report has a `COMMANDS:` line | `no COMMANDS line` |
| 3 | `scenario_change_committed` is `true` | `scenario change not committed` |

`pushed: true` does not make an attempt invalid; D2 step 6 deletes the remote branch.

### D5. Retry and failure of the scenario run

1. Attempt 1 invalid: the coordinator cleans up (D2 step 6) and runs attempt 2 with a fresh subject on branch `feat/w1-t05-<kind>-a2`, same base and same prompt. No further attempt follows attempt 2.
2. Attempt 1 or attempt 2 valid: the record gets `result` from the valid attempt; the coordinator continues with D6 (Step 4) or with the next paragraph (Step 1).
3. Both attempts invalid, or the D2 step 2 precondition failed: the record gets `result: "BLOCKED"`. The coordinator then dispatches nothing more in the stage of that step (Step 1: none of W1-T05, W1-T06, W1-T07 of `W1-P2`; Step 4: no W1-S3 task), does not run `swarm_schedule.py done` for that stage, and sends the owner this message, with the two `failure_reason` values substituted: `W1-T05 Step <1|4> BLOCKED (ADR 0042): attempt 1: <failure_reason>; attempt 2: <failure_reason>. Record: .swarm/gates/W1-T05-<kind>.json. Options: (a) retry the scenario run from attempt 1 (recommended when a failure_reason is AGENT_ERROR or TIMEOUT); (b) dispatch rootline-planner to re-plan the step.` The stage stays stopped until the owner chooses. When the precondition failed, the message has only the `attempt 1` part. Option (a) overwrites the record file.

**Step 1 outcome when the record is valid.**

- `result: "baseline-fails"` (the expected case): the coordinator dispatches the W1-T05 implementer (overview §7.5 step 2) and puts the full record JSON into the `details` input (an exception to the agent definition's rule that `details` is for fix modes only). The W1-T05 implementer executes Steps 2, 3 and 5 unchanged and writes in its report's `NOTES` line `baseline (ADR 0042): result=<result>, log_md_updated=<b>, ran_task_wiki_lint=<b>`.
- `result: "baseline-passes"`: the coordinator proceeds exactly as for `baseline-fails`. The skill is still written, because WIK-030 requires it and `tests/repo/test_skill.py` checks it; Step 4 then shows that the skill does not remove the behaviour. The record keeps `baseline-passes`, and the Step 4 `wiki/log.md` line (D6 step 3) states it.

W1-T06 and W1-T07 do not depend on the Step 1 result; the coordinator dispatches them after Step 1 has a valid record, in the same way as before this ADR (overview §7.5).

### D6. Step 4 verification (stage W1-S3)

1. The coordinator runs the scenario run of D2 with `<kind>` = `verify`, before any W1-S3 task. D4 and D5 apply unchanged; a `BLOCKED` result stops stage W1-S3 (D5 step 3).
2. `result: "verify-fails"`: W1-T05 is not done (overview §7.3). The coordinator dispatches the W1-T05 implementer with `mode: fix-review`, `branch: feat/w1-wiki-skill-deferred` from the current `origin/develop` tip, and `details` = both record files' JSON, to amend `.claude/skills/rootline-wiki/SKILL.md` so that the subject updates `wiki/log.md` and runs `task wiki:lint`; the reviewer reviews that branch as a sequential task; after it is squash-merged, the coordinator repeats D6 from step 1 with new attempt numbering on branches `feat/w1-t05-verify-a1` and `feat/w1-t05-verify-a2`. After 3 `verify-fails` results, the coordinator dispatches `rootline-planner` to re-plan W1-T05 (overview §7.5 step 4).
3. `result: "verify-passes"`: the coordinator appends one line under the `## <YYYY-MM-DD>` heading of the current UTC date in `wiki/log.md` (WIK-013; the heading is added when it is not the last heading), on branch `feat/w1-wiki-skill-deferred` from the current `origin/develop` tip (overview §7.3 "Commits around deferred steps"), with the values from the two record files substituted:

   `- [agent] W1-T05 Step 4 skill check passed (ADR 0042): baseline <baseline-fails|baseline-passes> (log_md_updated=<true|false>, ran_task_wiki_lint=<true|false>), with skill log_md_updated=true, ran_task_wiki_lint=true (commit <sha7>)`

   `<sha7>` is the first 7 characters of the Step 4 record's `base_sha`. The coordinator commits the line with the message `docs(wiki): record W1-T05 skill check` and the coordinator trailer (overview §7.1 "Commit attribution trailers"), pushes the branch and opens a PR into `develop`. The PR is reviewed and squash-merged as a sequential task (overview §7.6, last paragraph). This `wiki/log.md` line is the only place outside `.swarm/` where a baseline value is written; Step 1 writes nothing to `wiki/log.md`.

## Consequences

- W1-T05 Step 1 can run without the `writing-skills` skill, with the same scenario, model and recorded facts that the plan asked for, plus three extra facts (`ran_wiki_lint_script`, `scenario_change_committed`, `skill_present`) that make the comparison checkable.
- The W1 plan gets an "Amended" note under W1-T05 Step 1 that points at this ADR and covers Steps 1 and 4 (`docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`, "Task W1-T05"). The schedule YAML is unchanged (`pre_steps: [1]`, `deferred_steps: [4]`, `deferred_to: W1-S3`), so the wave-file "Execution schedule" table is unchanged.
- `ran_task_wiki_lint` is based on the subject's own `COMMANDS:` line, not on an independent trace. This is accepted: both runs use the same reporting, and `log_md_updated` is checked from git, independently of the report.
- The baseline record is not committed (`.swarm/` is ignored, ADR 0037); its result survives in the W1-T05 implementer's report and in the Step 4 `wiki/log.md` line.
- The next free ADR number is 0043.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| The coordinator writes the `writing-skills` process from memory | The coordinator must not invent a skill it cannot load; the result would be unverifiable and would differ between sessions |
| Ask the owner to install the `writing-skills` skill | Adds an owner step and a dependency outside the repository for a check this ADR defines fully with existing tools |
| Drop the baseline and keep only the Step 2 red-green test | The red-green test checks the file's text, not agent behaviour; WIK-030's purpose is the behaviour, so the before/after comparison stays |
| Record the baseline in `wiki/log.md` at Step 1 | The W1-T05 plan text records only the Step 4 result there; a Step 1 log line would need its own branch and PR before `W1-P2` starts |
| Detect `task wiki:lint` with a `task` wrapper placed on the subject's `PATH` | Needs a new script and a changed environment for one check; the self-reported command list plus git inspection is simpler |
| Dispatch the subject without `isolation: "worktree"` | The subject would change the coordinator's own checkout at `/home/arkhash0309/projects/rootline` |

## Spec references

WIK-013, WIK-020, WIK-030, PG-16, PG-23, ADR 0035, ADR 0037, overview §7.3, §7.5, §7.6, W1-T05 (Steps 1 to 5), W1-T06, W1-T07, spec §0.3, spec §26.
