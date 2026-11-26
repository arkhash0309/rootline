# 0040 — Swarm tooling plan amendments from the W1-T16 review (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-21 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

The review of W1-T16 (branch `feat/w1-swarm-tooling`, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T16") found places where the plan and the overview protocol (overview §7) either conflict with the lint rules of the root `pyproject.toml` or leave a behaviour of the swarm tooling unstated. The implementer had to decide each of them. The spec and the plans do not answer these questions (lettered A to K; each Decision item below names the Context letters it answers):

- **A.** The root `pyproject.toml` selects ruff rules `["E", "F", "W", "I", "UP", "B", "S", "ASYNC", "RUF"]` and ignores only `S101`. Ruff `0.17.6` reports `S603` ("`subprocess` call: check for execution of untrusted input") on `subprocess` calls whose argument list it cannot verify, for example `subprocess.run(cmd)` where `cmd` is a variable, and `S607` ("Starting a process with a partial executable path") on every call whose executable is a bare name such as `"git"` or `"helm"`. Overview Global Constraints "Formatting" (PG-19, ADR 0038) says a `ruff check` finding is fixed by hand, never by disabling the rule. A subprocess wrapper such as `scripts.proc.run` cannot avoid `S603`, because its argument list is a parameter. The plan's `scripts/proc.py` block (W1-T06 Step 2) has no suppression, so the file copied from the plan fails `uv run ruff check`.
- **B.** The plan's `health.py` block (W1-T07 Step 3) carries `# noqa: BLE001`. Rule family `BLE` is not selected, so ruff reports `RUF100` ("Unused `noqa` directive (non-enabled: `BLE001`)") on that line.
- **C.** Other plan blocks also fail `uv run ruff check` as written: the W1-T02 Step 1 test has `import subprocess, sys` on one line (`E401`), imports `pytest` without using it (`F401`) and lists `version_of, validate` out of order (`I001`); the W1-T03 Step 1 test imports `subprocess` without using it (`F401`) and builds `files + ["index.md", "status.md"]` (`RUF005`); the W1-T06 Step 3 `scripts/doctor.py` block has an f-string line longer than 110 characters that `ruff format` cannot split (`E501`); the W1-T03 Step 3 `scripts/wiki_lint.py` block, the W1-T10 Step 1 test and the W1-T11 Step 1 test call `subprocess.run(["git", …])` or `subprocess.run(["helm", …])` (`S603` and `S607`).
- **D.** Overview §7.7 lists the `exec` smoke check keys as `{pod_selector, container, command, expect_exit: 0}` and does not say which namespace `kubectl exec` runs in.
- **E.** Overview §7.9 step 1 says `swarm_schedule.py next --week <N>` "prints the next runnable stage", but not what it prints or which exit code it returns when the week is complete, when no stage is runnable, or when the week does not exist.
- **F.** W1-T16 "Execution schedule" text says `table --week N` "must print exactly this table", but not whether `validate` checks it.
- **G.** W1-T16 Step 3 computes changed files with `git diff --name-only --diff-filter=ACMRD`, which reports a rename as one path (the new name), so a task could move a file out of another task's ownership unchecked. The CLI interface lists exit codes 0 and 1 only and says nothing about an unknown task or a failing `git` command.
- **H.** W1-T16 "Interfaces" calls `swarm_lib.matches` "gitignore-style via `pathspec`". In gitignore syntax a pattern without `/` (for example `pyproject.toml`) matches at every directory depth, which would make an ownership glob broader than its author wrote.
- **I.** Overview §7.7 G1 says "`check_ownership.py` passes for every task of the stage". On `integration/<stage>` the branch holds the changes of every task of the stage, so a per-task check fails for every path that another task of the same stage owns.
- **J.** The gate's check names, how a check runs a command inside the gate worktree (`scripts.proc.run` has no `cwd` parameter), the per-command timeout, what happens when `git worktree add` or the worktree's `uv sync` fails, which exit code an unknown stage or an unresolvable ref gives, and which part of `eval/baselines/baseline-smoke.json` G10 compares (the file also holds `git_sha`, which differs on every commit, W4-T14 Step 4b) are not stated.
- **K.** Scripts are run as `uv run python scripts/<name>.py` (Taskfile variable `PY: uv run python`, W1-T06 Step 4), which puts `scripts/` itself, not the repository root, first on `sys.path`. The root project is `package = false`, so `uv sync` does not install the repository root either. The plan blocks of `scripts/render_versions.py` (W1-T02 Step 4), `scripts/doctor.py` (W1-T06 Step 3) and `scripts/render_workload.py` (W1-T09 Step 4) import `from scripts.<module> import …` at the top, which raises `ModuleNotFoundError: No module named 'scripts'` when the script is run that way. `pythonpath = ["."]` in `[tool.pytest.ini_options]` fixes this only under pytest.

## Decision

Each item below follows spec §0.3 (simplest, cheapest, safest). None changes cost, security posture or scope.

### 1. Lint suppressions: `S603` only, with a same-line justification

Answers Context A, B and C.

| Rule | Decision |
|---|---|
| `S603` | Allowed. A `subprocess` call whose argument list is a parameter, a variable, a list literal with non-literal elements, or a list built in code carries `# noqa: S603 - <justification>` on the line where ruff `0.17.6` reports `S603`, with the justification on that same line, and only where `uv run ruff check` reports `S603`, because an unused `# noqa: S603` fails with `RUF100`. The reported line is the one holding `subprocess.run(` or `subprocess.Popen(`. The justification follows ` - ` and states why no shell or untrusted input is involved, for example `# noqa: S603 - cmd is an argument list run without a shell (GEN-041)`. Verified on ruff `0.17.6`: `subprocess.run([sys.executable, "scripts/render_versions.py", "--check"], cwd=REPO)` is not reported, so the W1-T02 Step 1 test carries no `noqa`. Files that need the comment at W1-T16: `scripts/proc.py` (one call) and `scripts/cluster_smoke.py` (the `subprocess.Popen` of the port-forward). |
| `S607` | Not suppressed. Code that starts a program by a bare name (`git`, `helm`, `kubectl`, `uv`) calls `scripts.proc.run(cmd, …)` instead of `subprocess` directly; ruff does not report `S607` or `S603` at a `scripts.proc.run` call site, because the call inside `proc.run` passes a variable. A test that runs `git` in a temporary repository uses `scripts.proc.run(["git", "-C", str(root), …])` (`proc.run` has no `cwd` parameter). |
| `BLE001` | Not used. `# noqa: BLE001` is never written, because rule family `BLE` is not selected and the comment fails with `RUF100`; a deliberate broad handler is written `except Exception:` or `except Exception as <name>:`, followed on the same line by `# <justification>`. Example: `except Exception:  # any exception from a readiness check means not ready (ARC-020)`. |
| Every other rule | No suppression of any other rule is allowed by this ADR. A finding is fixed in the code, per overview Global Constraints "Formatting". |

Overview Global Constraints "Formatting" states the `S603` and `BLE001` sentences above word for word. The plan blocks are amended to the lint-clean text: W1-T02 Step 1 test (`import subprocess` and `import sys` on two lines, no `import pytest`, import list `CONSTRAINTS, load_versions, validate, version_of`), W1-T02 Step 4 `scripts/render_versions.py` (`sys.path.insert`, item 9), W1-T03 Step 1 test (no `import subprocess`; `[*files, "index.md", "status.md"]`), W1-T03 Step 3 `scripts/wiki_lint.py` (`scripts.proc.run(["git", "-C", str(REPO), …], check=False)`, `sys.path.insert`), W1-T06 Step 2 `scripts/proc.py` (final text with the `S603` comment), W1-T06 Step 3 `scripts/doctor.py` (`sys.path.insert`; the `repo-location` detail is built from a `location` variable so no line exceeds 110 characters, same output text), W1-T07 Step 3 `health.py` (`except Exception:` with justification), W1-T09 Step 4 `scripts/render_workload.py` (`sys.path.insert`), W1-T10 Step 1 and W1-T11 Step 1 tests (`scripts.proc.run(["helm", …])`).

Verification (2026-11-27): each of these ten blocks was written to its target path in a scratch directory holding a copy of the root `pyproject.toml` (and an empty `scripts/__init__.py`, so `scripts` sorts as first-party), then `ruff format <path>` and `ruff check <path>` were run with ruff `0.17.6`. Every block reported `All checks passed!`, and no line was longer than 110 characters after `ruff format`. A task that copies one of these blocks and runs `uv run ruff format` then `uv run ruff check` (overview Global Constraints "Formatting") therefore gets no finding; the only differences from the block are those `ruff format` makes.

### 2. `exec` smoke checks require `namespace`

Answers Context D.

Every check of kind `exec` in `tests/smoke/<component>.yaml` has the required keys `name`, `kind`, `namespace`, `pod_selector`, `container`, `command`, `expect_exit`. `scripts/cluster_smoke.py` looks up the pod with `kubectl --context <ctx> -n <namespace> get pods -l <pod_selector> -o jsonpath={.items[0].metadata.name}` and runs `kubectl --context <ctx> -n <namespace> exec <pod> -c <container> -- <command…>`. A file without `namespace` on an `exec` check fails validation against `tests/smoke/schema.json`. Overview §7.7 lists the keys.

### 3. `swarm_schedule.py next --week N` output and exit codes

Answers Context E.

| Situation | Printed line (stdout, exact) | Exit code |
|---|---|---|
| A stage of week N is not in `.swarm/progress.json` `done` and all its `after` stages are | the ID of the first such stage in schedule order, for example `W1-P2` | 0 |
| Every stage of week N is in `done` | `week N complete` (with the number, for example `week 1 complete`) | 0 |
| Week N has stages not in `done`, but none is runnable | `no runnable stage in week N; not done: <ids>`, `<ids>` = the not-done stage IDs of week N in schedule order joined by `, ` | 1 |
| Week N is not in the schedule | `unknown week: N` | 1 |

Overview §7.9 step 1 carries this table.

### 4. `validate` checks the wave-file tables

Answers Context F.

`uv run python scripts/swarm_schedule.py validate` also renders the "Execution schedule" table of every week from the YAML (the output of `table --week N`) and compares it, character for character, with the table under `## Execution schedule` in the one wave file `docs/superpowers/plans/*-w<N>-*.md`. All eight wave files must match. Error lines: `W<N>: expected exactly one wave file matching *-w<N>-*.md`, `W<N>: <file> has no execution schedule table`, `W<N>: execution schedule table in <file> differs from the YAML (print it with: uv run python scripts/swarm_schedule.py table --week <N>)`. Any error line → exit 1.

### 5. `check_ownership.py` change detection and exit codes

Answers Context G.

Changed files are `git diff --name-only --diff-filter=ACMRD --no-renames -z <base>...<branch>`, split on NUL. With `--no-renames`, a rename is reported as a deletion of the old path plus an addition of the new path, and both paths are checked. Exit codes: 0 every changed path passes; 1 at least one path fails (one stdout line per path); 2 unknown task or stage, or a `git` command exited non-zero (one stderr line: `unknown task: <id>`, `unknown stage: <id>` or `git <args> failed: <stderr>`).

### 6. `swarm_lib.matches` anchoring

Answers Context H.

`matches(path, globs)` uses `pathspec.GitIgnoreSpec` with one change: a pattern that contains no `/` is anchored at the repository root (it is compiled as `/` + pattern). So `pyproject.toml` matches only the root `pyproject.toml`, and `**/pyproject.toml` matches it at every depth. This is narrower than gitignore, on purpose: an ownership glob never covers more than its author wrote. Overview §7.2 and the schedule YAML header state the rule.

### 7. G1 on an integration branch: union of the stage's ownership

Answers Context I.

| Where | Command | A changed path passes when |
|---|---|---|
| Task branch of a parallel task (§7.4) | `uv run python scripts/check_ownership.py --task <task id> --base <stage base sha> --branch <task branch>` | it matches that task's `owns` and no glob of its `excludes`, or it matches `always_allowed` and satisfies that path's §7.4 special rule |
| Integration branch `integration/<stage>` (G1) | `uv run python scripts/check_ownership.py --stage <stage id> --base <base sha> --branch <head sha>` | it matches the `owns` minus `excludes` of at least one task of the stage, or it matches `always_allowed` and satisfies that path's §7.4 special rule |

Offending-path lines: `ownership: <path> not owned by <task id>` (`--task`) and `ownership: <path> not owned by any task of <stage id>` (`--stage`). Exactly one of `--task` and `--stage` is required. A sequential stage has no `owns` lists, so `--stage` on a sequential stage exits 0, and G1 is `skip` with reason `stage <id> is sequential`. G1 is `pass` on exit 0 and `fail` with reason `exit <code>` on exit 1 or 2. Overview §7.7 G1 states this rule.

### 8. Gate check names, command runner, timeout, setup, exit codes and G10

Answers Context J.

| Topic | Decision |
|---|---|
| Check names | Every entry of `checks` in `.swarm/gates/<stage>.json` has `name` = `G<n> <label>`. The full list, in run order: `G1 ownership`, `G2 uv-lock`, `G2 npm-ci`, `G3 versions`, `G3 contracts`, `G3 prompt-hashes`, `G3 scenarios`, `G4 alembic-heads`, `G4 migrations-test`, `G5 ruff`, `G5 ruff-format`, `G5 mypy`, `G5 eslint`, `G5 tsc`, `G5 helm-lint`, `G5 kubeconform`, `G5 terraform-fmt`, `G5 terraform-validate`, `G5 tflint`, `G5 opa-fmt`, `G6 pytest`, `G6 console`, `G6 opa`, `G6 kyverno`, `G7 coverage`, `G8 registry`, `G9 test-count`, `G10 replay`, `G11 wiki`. A check function that raises is recorded under its name from this list with status `fail` and reason `internal error: <repr of the exception>`; the gate continues with the next check |
| Command runner | The default runner runs `["env", "--chdir", "<directory>", *cmd]` through `scripts.proc.run(…, check=False, timeout=3600)`, because `scripts.proc.run` has no `cwd` parameter. On Ubuntu 26.04 `env` is uutils coreutils `0.10.0` (`/usr/lib/cargo/bin/coreutils/env`); `env --chdir /tmp pwd` printed `/tmp` there on 2026-11-27. GNU coreutils `env` (CI runners) has `--chdir` since coreutils 8.28 |
| Timeout | 3600 s per command. On `subprocess.TimeoutExpired` the runner returns exit code `124` with stderr `timeout after 3600 s: <command joined by spaces>`; the check reports `fail` with reason `exit 124` |
| Exit 2 | `integration_gate.py` exits 2, before it creates a worktree or writes a report, for an unknown stage (stderr `unknown stage: <id>`) or for a `--base` or `--branch` ref that `git rev-parse --verify <ref>^{commit}` cannot resolve (stderr `cannot resolve base <ref>` or `cannot resolve branch <ref>`). `--report-only` does not change exit 2 |
| Setup worktree | The gate creates `.swarm/worktrees/<stage>` (branch) and then `.swarm/worktrees/<stage>-base` (base) with `git worktree add --detach <path> <sha>`. If either `git worktree add` exits non-zero, the report's `checks` holds exactly one entry `{name: "setup worktree", status: "fail", reason: "git worktree add <path> failed: <git stderr>", duration_s: 0.0, output_tail: ""}`, `uv sync` and the G-checks do not run, any worktree already created is removed, the report is written, and the gate exits 1 (exit 0 with `--report-only`) |
| Setup uv-sync | After both worktrees exist, the gate runs `uv sync --all-packages --frozen` in the branch worktree. If it exits non-zero, the report's `checks` holds exactly one entry `{name: "setup uv-sync", status: "fail", reason: "exit <code>", duration_s: 0.0, output_tail: <last 40 lines>}`, no G-check runs, both worktrees are removed, the report is written, and the gate exits 1 (exit 0 with `--report-only`) |
| G10 | Runs `uv run rootline-eval baseline --split smoke --write-regression <temporary file>` in the branch worktree and compares only the value of the top-level key `results` of the temporary file with the `results` value of the committed `eval/baselines/baseline-smoke.json` (parsed JSON, compared as values). Other top-level keys (`git_sha`) are ignored. Equal → `pass`. Different → `fail`, unless the PR body has a line `baseline-change: <reason>` and the committed file differs from the base's file (`pass` with reason `baseline-change exemption; baseline file updated in this PR`) |

These are recorded in W1-T16 "Interfaces".

### 9. Scripts importing `scripts.*`

Answers Context K.

A script under `scripts/` that imports from the package `scripts` and is run as `uv run python scripts/<name>.py` has, after its standard-library and third-party imports and before its first `from scripts` import, exactly this line:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

(with `import sys` and `from pathlib import Path` among its imports). Ruff `E402` allows imports after a `sys.path` modification. The W1-T16 scripts already do this; the plan blocks of `scripts/render_versions.py` (W1-T02 Step 4), `scripts/wiki_lint.py` (W1-T03 Step 3), `scripts/doctor.py` (W1-T06 Step 3) and `scripts/render_workload.py` (W1-T09 Step 4) now include it.

## Consequences

- W1-T16's implementer applies items 1 to 8 to `scripts/` and `tests/repo/` on the fix branch `fix/w1-t16-adr-0040`: the `S603` justification moves onto the `noqa` line in `scripts/proc.py` and `scripts/cluster_smoke.py`; `tests/repo/test_integration_gate.py` replaces its direct `subprocess.run([...git...])  # noqa: S603` / `# noqa: S607` with `scripts.proc.run`; `scripts/check_ownership.py` gains `--stage`; G1 in `scripts/integration_gate.py` calls `check_ownership.py --stage`. `fix/w1-t16-adr-0040` MUST be merged into `develop` before stage W1-P1 is dispatched, because the `scripts/proc.py` merged with W1-T16 has a bare `# noqa: S603` on line 21 that the W1-T06 Step 2 check (`diff` against the plan block) rejects.
- The tasks that copy the amended blocks (W1-T02, W1-T03, W1-T06, W1-T07, W1-T09, W1-T10, W1-T11) get no `uv run ruff check` finding after `uv run ruff format` (verified per block, item 1).
- `swarm_schedule.py validate` fails whenever a wave file's table and the YAML differ, so every schedule change touches both (planner rule 5 in `.claude/agents/rootline-planner.md`).
- W1-T04 must not reuse number 0040; the next free ADR number after W1-T04 is 0041. W1-T03 lists `adr/0040-swarm-plan-amendments-w1-t16.md` in `wiki/index.md`.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Add `S603` and `S607` to `[tool.ruff.lint] ignore` | Disables the checks for the code of weeks 3 to 5 that builds commands from request input (MCP servers, the gate service) |
| `per-file-ignores` for `scripts/**` and `tests/**` | Same loss of coverage for the whole directory; one wrapper with one justified comment is narrower |
| Allow `# noqa: S607` next to `S603` | `scripts.proc.run` removes the need, so no second suppression is required |
| Select `BLE` so `# noqa: BLE001` is used | Adds a rule family for one line; the justification comment documents the intent without it |
| Justification on the line above the `noqa` | `grep -n 'noqa'` and a reviewer reading the diff hunk then see the suppression without its reason; the same line keeps both together |
| G1 runs the per-task check for every task on the integration branch | Fails on every integration branch with more than one task |
| Plain gitignore semantics in `matches` | A slash-less glob would match at every depth, broader than written |
| Install the repository root as a package (`package = true`) | Turns `rootline-workspace` into a built package and changes `uv.lock`; one `sys.path` line per script is smaller |

## Spec references

PG-16, PG-19, PG-21, CI-001, GEN-041, ARC-020, overview Global Constraints "Formatting", overview §7.2, §7.4, §7.7, §7.9, W1-T02, W1-T03, W1-T04, W1-T06, W1-T07, W1-T09, W1-T10, W1-T11, W1-T16, ADR 0035, ADR 0038, spec §0.3, spec §26.
