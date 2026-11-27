# 0045 — CI workflow and ruleset decisions from the W1-T14 review (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-26 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

The review of W1-T14 (CI workflow `ci.yml` and repository ruleset, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T14", branch `feat/w1-ci` at `8b2ce1c`) found six gaps in the plan text. In each case the plan did not say what to do, or said two contradicting things. The gaps are lettered A to F, and decision D<n> answers letter n (D1 answers A, D6 answers F).

- **A. Test file not owned.** `scripts/ci_changed_files.py` is in W1-T14 "Files" and in the W1-T14 `owns` list of `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`, but no test file for it is listed. W1-T14 runs in the parallel stage W1-P3, so a test file outside `owns` fails `scripts/check_ownership.py --task W1-T14` and integration gate check G1 (overview §7.4, §7.7). Without a test, the script is untested code in the CI path of WIK-020.
- **B. `scripts/ci_changed_files.py` has no interface.** The plan lists the file but defines no command line, output format, exit codes or error messages. On `8b2ce1c` the script handles only a `git` non-zero exit; a missing `git`, a timeout, a missing `--repo` directory and an unwritable `--output` path end in a Python traceback.
- **C. Status check name.** GEN-020 and the plan ruleset JSON require the status check context `ci / required`. GitHub matches a ruleset's required status check against the check-run name, and a GitHub Actions check run is named after the job's `name` (the job ID when `name` is absent), not `<workflow> / <job>`. The plan's `required` job had no `name`, so its check run is named `required` and the required context `ci / required` would never be reported: every PR into `main` and `develop` would wait for it forever.
- **D. Linear history on `main`.** GEN-020 (spec §4.3, table row `main`, column "Protection") lists "linear history". GEN-021 requires the release PR `develop → main` to merge with a merge commit. A `required_linear_history` rule rejects merge commits, so the two requirements cannot both hold. The W1-T14 Step 3 text listed `{"type":"required_linear_history"}` in `main.json` and, in the next sentence, said to omit it.
- **E. Tool versions in CI.** GEN-050 pins every tool in `versions.yaml`, rendered into `.github/versions.env` (W1-T02). The plan's `ci.yml` read `V_UV` only in the `python` job; `astral-sh/setup-uv` in `manifests`, `contracts`, `wiki` and `security` had no `version`, so those jobs installed the latest `uv`. `aquasecurity/trivy-action` and `gitleaks/gitleaks-action` had no version input, so they used whatever their action release defaults to, although `versions.yaml` pins `trivy` `0.76.2` and `gitleaks` `8.30.1`. The plan also did not say which Python the four jobs other than `python` use.
- **F. Where action SHAs are recorded.** W1-T14 Step 1 says to pin every third-party action by commit SHA and record the SHAs in `wiki/versions.md`. That file is owned by W1-T02 (schedule YAML W1-T02 `owns`, PG-22) and excluded from W1-T03, so W1-T14 (stage W1-P3) may not edit it, and W1-T02 Step 8, which writes the page, did not mention actions.

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). None of them changes cost or scope. D4 removes a protection rule from `main`; it does not weaken anything the owner approved beyond what GEN-021 already requires, because the approved plan (W1-T14 Step 3) already said to omit the rule, and the rule would make every release PR unmergeable. The plan text is amended in the same PR as this ADR.

### D1 — Test file in W1-T14 `owns` (A)

1. `tests/repo/test_ci_changed_files.py` is added to the W1-T14 `owns` list in `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml` (stage W1-P3), after `scripts/ci_changed_files.py`. The W1-T14 "Files" list gains `Test: tests/repo/test_ci_changed_files.py`, under an amendment note below the task header.
2. The module docstring of `tests/repo/test_ci_changed_files.py` cites CI-001, WIK-020 and PG-21, and every test function's docstring cites at least one of those three IDs. PG-21 is cited because the change-set rule (`--diff-filter=ACMRD --no-renames`, rename = deletion plus addition) is the PG-21 rule of `scripts/check_ownership.py`.
3. The tests are the eleven cases of the table "Required tests" in W1-T14 "Interfaces" (plan). They build throw-away repositories under pytest's `tmp_path` with `git` through `scripts.proc.run`, as `tests/repo/test_check_ownership.py` does, and make no network call.
4. The wave-file "Execution schedule" table does not change, because it does not list owned paths.

### D2 — Interface of `scripts/ci_changed_files.py` (B)

Command line (run from the repository root):

```
uv run python scripts/ci_changed_files.py --base <ref> --head <ref> [--output <file>] [--repo <dir>]
```

| Option | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `--base` | string (git revision) | yes | — | Base revision, for example `origin/develop` |
| `--head` | string (git revision) | yes | — | Head revision, for example `HEAD` |
| `--output` | file path | no | none: write to stdout | File to write (UTF-8, created or overwritten); relative paths resolve against the working directory |
| `--repo` | directory path | no | the repository that contains the script (`Path(__file__).resolve().parents[1]`) | Repository passed to `git -C` |

Behaviour:

1. If `--repo` is not an existing directory (`Path(repo).is_dir()` is `False`), the script fails with reason `repo not found: <dir>` before it starts `git`.
2. It runs, through `scripts.proc.run` with `check=True` and `timeout=120` (seconds), the argument list `["git", "-C", <repo>, "diff", "--name-only", "--diff-filter=ACMRD", "--no-renames", "-z", "<base>...<head>"]`. No shell is involved. The three-dot form compares `<head>` with the merge base of `<base>` and `<head>`, so commits that reached `<base>` after the branch point are not listed. `--no-renames` lists a rename as the deleted old path and the added new path (PG-21).
3. It splits `git`'s stdout on NUL (`\0`), drops empty strings, sorts the paths with Python `sorted()` (code-point order), removes nothing else (duplicates cannot occur in `git diff --name-only` output), and joins them as `"".join(f"{p}\n" for p in paths)`: one path per line, each line ending in LF, no other characters. An empty change set gives the empty string.
4. With `--output`, it writes that text in one `Path(output).write_text(text, encoding="utf-8")` call and writes nothing to stdout. Without `--output`, it writes the text to stdout.
5. It writes no other file, never changes the repository and makes no network call. It does not validate ref syntax; `git` does. Callers MUST pass refs that do not start with `-` (CI passes `origin/<base_ref>` and `HEAD`).

Outputs and exit codes. Every handled failure prints exactly one stderr line `ci_changed_files: <reason>` and exits `2`; on a failure before step 4 nothing is written to stdout and no `--output` file is created or changed.

| Case | When it occurs | stderr (exact) | Exit |
|---|---|---|---|
| Success | `git` exits 0 and the output is written | nothing | 0 |
| Repository missing | `--repo` is not an existing directory | `ci_changed_files: repo not found: <dir>` (`<dir>` = the `--repo` value as given, or the default path) | 2 |
| `git` missing | starting `git` raises `FileNotFoundError` | `ci_changed_files: git missing` | 2 |
| Timeout | `git` does not finish within 120 s (`subprocess.TimeoutExpired`) | `ci_changed_files: timeout` | 2 |
| `git` exits non-zero | unknown revision, no merge base, `--repo` is a directory that is not a git repository | `ci_changed_files: git failed: <msg>`, where `<msg>` is the first line of `git`'s stderr after `.strip()`, or `exit <returncode>` when that stderr is empty. Example with git `2.53.0`: `ci_changed_files: git failed: fatal: ambiguous argument 'origin/nope...HEAD': unknown revision or path not in the working tree.` | 2 |
| `git` cannot be started for another reason | starting `git` raises an `OSError` other than `FileNotFoundError` (for example `PermissionError`) | `ci_changed_files: git failed: <str(exc)>` | 2 |
| `git` output not UTF-8 | decoding `git`'s stdout raises `UnicodeDecodeError` | `ci_changed_files: git failed: <str(exc)>` | 2 |
| Output not writable | `--output` is given and `write_text` raises `OSError` (parent directory missing, path is a directory, permission denied) | `ci_changed_files: output not writable: <path>` (`<path>` = the `--output` value as given). The script does not retry and does not delete a partly written file | 2 |
| Usage error | `--base` or `--head` missing, unknown option | argparse's own two lines (`usage: …` and `ci_changed_files.py: error: <message>`) | 2 |

These are the only failures the script handles. Any other exception is a defect in the script and ends with Python's traceback and exit 1.

Python interface (used by the tests):

| Name | Signature | Contract |
|---|---|---|
| `ChangedFilesError` | `class ChangedFilesError(Exception)` | `str(exc)` is the reason text without the `ci_changed_files: ` prefix, for example `timeout` |
| `changed_files` | `changed_files(base: str, head: str, repo: Path = REPO, *, timeout: int = 120) -> list[str]` | Steps 1 to 3 above; returns the sorted paths; raises `ChangedFilesError` with reason `repo not found: <dir>`, `git missing`, `timeout` or `git failed: <msg>` |
| `main` | `main(argv: Sequence[str] \| None = None) -> int` | Parses arguments, calls `changed_files`, writes the output (step 4), maps `ChangedFilesError` and the output `OSError` to the stderr line and returns the exit code of the table |

`.github/workflows/ci.yml` job `wiki`, step for `pull_request` events, runs `uv run python scripts/ci_changed_files.py --base "origin/${{ github.base_ref }}" --head HEAD --output changed.txt` and passes `changed.txt` to `scripts/wiki_lint.py --changed-files` (WIK-020). A non-zero exit fails the step, so the job and `ci / required` fail.

### D3 — Status check name (C)

The `required` job of `.github/workflows/ci.yml` has `name: ci / required`. Its check run is then named `ci / required`, which is the context required by both rulesets (`.github/rulesets/main.json`, `.github/rulesets/develop.json`) and by GEN-020. The job ID stays `required`. In the PR checks list GitHub shows it as `ci / ci / required`; only the check-run name matters for the ruleset.

Verification runs in the deferred W1-T14 Steps 2 and 3 at the start of stage W1-S3 (schedule YAML W1-T14 `deferred_steps: [2, 3]`, `deferred_to: W1-S3`):

| Step | Command | Expected |
|---|---|---|
| 2 | `gh api "repos/arkhash0309/rootline/commits/$(git rev-parse origin/develop)/check-runs" --jq '.check_runs[] \| select(.name == "ci / required") \| .conclusion'` | exactly one line `success` |
| 3 | `gh api repos/arkhash0309/rootline/rules/branches/develop --jq '.[] \| select(.type == "required_status_checks") \| .parameters.required_status_checks[].context'` | exactly one line `ci / required` |
| 3 | `gh api repos/arkhash0309/rootline/rules/branches/main --jq '.[] \| select(.type == "required_status_checks") \| .parameters.required_status_checks[].context'` | exactly one line `ci / required` |
| 3 | `gh api repos/arkhash0309/rootline/rules/branches/main --jq '[.[].type] \| sort \| join(",")'` | `deletion,non_fast_forward,pull_request,required_status_checks` (no `required_linear_history`, D4) |

If Step 2 prints nothing, the job name does not match: the coordinator stops W1-S3 and sends W1-T14 back to its implementer on `feat/w1-ci-deferred`. If Step 3 prints anything else, the coordinator stops W1-S3 and asks the owner, because the rulesets are an **[OWNER]** step (O-3).

### D4 — No linear-history rule on `main` (D)

1. `.github/rulesets/main.json` has no `{"type":"required_linear_history"}` rule. Its rules are exactly, in this order: `deletion`, `non_fast_forward`, `pull_request` (parameters as in W1-T14 Step 3), `required_status_checks` (context `ci / required`, `strict_required_status_checks_policy: false`). `bypass_actors` is the repository admin role (actor ID `5`, `RepositoryRole`, `always`).
2. `.github/rulesets/develop.json` is `main.json` with `name` `protect-develop`, `include` `["refs/heads/develop"]`, the same four rules, and no `bypass_actors` key.
3. GEN-021 wins over GEN-020 because it is the more specific rule (it names the merge method of the release PR). The exact spec change is in GEN-020 (spec §4.3), table row `main`, column "Protection": the item `linear history` is replaced by `no linear-history rule (GEN-021 release merge commits; PG-26, ADR 0045)`. The text of that cell becomes: "Ruleset: PR required; required checks `ci / required`; no force-push; no deletion; no linear-history rule (GEN-021 release merge commits; PG-26, ADR 0045); bypass: owner only". A note paragraph below the GEN-020 table states the conflict. No other GEN-020 row changes, and GEN-021 does not change.
4. `wiki/adr/0025-branching.md` gains a section `## Amendment 2026-11-27 (PG-26, ADR 0045)` that states the same change.
5. SEC-081 (ruleset `protect-main` on `rootline-env`, "require linear history") is not affected: `rootline-env` PRs merge by squash, which keeps history linear.

### D5 — Tool versions in CI (E)

Every `ci.yml` job that installs a pinned tool reads its version from `.github/versions.env`, loaded by the step `run: cat .github/versions.env >> "$GITHUB_ENV"` placed after `actions/checkout` and before the first step that uses a `V_*` value.

| Job | Step | Input | Value |
|---|---|---|---|
| `python`, `manifests`, `contracts`, `wiki`, `security` | `astral-sh/setup-uv` | `with: version` | `"${{ env.V_UV }}"` (`0.13.10` on the pin date) |
| `python` | `run: uv python install ${{ env.V_PYTHON }}` | — | `3.12.16` on the pin date |
| `infra` | `aquasecurity/trivy-action` | `with: version` | `"v${{ env.V_TRIVY }}"` (the action expects a `v` prefix: `v0.76.2`) |
| `security` | `gitleaks/gitleaks-action` | step `env: GITLEAKS_VERSION` | `"${{ env.V_GITLEAKS }}"` (no `v` prefix: `8.30.1`) |

The jobs `manifests`, `contracts`, `wiki` and `security` do not run `uv python install`. They accept any CPython 3.12.x that satisfies `requires-python = ">=3.12,<3.13"` of the root `pyproject.toml`: `uv` uses the runner's system Python 3.12 or downloads a 3.12 build. This is an explicit choice (cheapest: no extra step, no extra minutes under CI-002); these jobs run scripts and pytest on repository files only, and the `python` job is the one that tests the code with the pinned `3.12.16`. Jobs `console`, `policy` and `infra` already read `V_NODE`, `V_OPA`, `V_KYVERNO_CLI`, `V_TERRAFORM` and `V_TFLINT`; `manifests` reads `V_KUBECONFORM`. `azure/setup-helm` keeps its default Helm version, because `versions.yaml` has no Helm CLI key.

### D6 — Where action SHAs are recorded (F)

1. The commit SHA and tag of each third-party action are recorded only in `.github/workflows/ci.yml`, on the `uses:` line, in the form `uses: <owner>/<repo>@<40-hex sha> # v<X.Y.Z>`. W1-T14 does not edit `wiki/versions.md`.
2. W1-T02 Step 8 (already deferred to stage W1-S3, schedule YAML W1-T02 `deferred_steps: [8]`, `deferred_to: W1-S3`) also writes a section `## GitHub Actions` into `wiki/versions.md`: a table `| Action | Tag | Commit SHA |` with one row per distinct `<owner>/<repo>` in the `uses:` lines (item 3) of `.github/workflows/ci.yml` on `origin/develop` at the start of W1-S3, sorted by `Action`; `Tag` is the text after `# ` and `Commit SHA` is the 40-hex value after `@`. W1-S3 starts after the W1-P3 integration PR (which contains `ci.yml`) has merged, so the file exists.
3. A `uses:` line is a line of `ci.yml` that matches `^\s*(-\s+)?uses:`. Every such line MUST match `^\s*(-\s+)?uses:\s+([\w.-]+/[\w.-]+)@([0-9a-f]{40})\s+#\s+(v\S+)\s*$` (group 2 = `Action`, group 3 = `Commit SHA`, group 4 = `Tag`). If `ci.yml` is absent, or a `uses:` line does not match, or one `Action` appears with two different SHAs, W1-T02 Step 8 reports `STATUS: BLOCKED` with the line, and the coordinator sends W1-T14 back to its implementer.
4. The schedule YAML gets a comment on the W1-T02 `deferred_steps` line naming this addition. The data does not change, so the wave-file table does not change.
5. Every PR merged after W1-T02 Step 8 that changes an action SHA in `ci.yml` MUST update the matching `## GitHub Actions` row of `wiki/versions.md` in the same PR (GEN-051).

## Consequences

- `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T14" changed on 2026-11-27 on branch `docs/w1-t14-ci-decisions`: amendment note, Requirement IDs (PG-26), "Files" (rulesets and test file), new "Interfaces" section (D2 and the required tests), the Step 1 `ci.yml` block (D3, D5), the paragraph after it (D5, D6), the new Step 1b (D1, D2), Steps 2 and 3 (D3 verification, D4 JSON). "Task W1-T02" Step 8 gained the `## GitHub Actions` section (D6) and its amendment note names PG-26.
- `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`: W1-T14 `owns` gains `tests/repo/test_ci_changed_files.py`; the W1-T02 `deferred_steps` line gains a comment. `uv run python scripts/swarm_schedule.py validate` prints `schedule OK: 8 weeks, 39 stages, 94 tasks`.
- Spec `docs/superpowers/specs/2026-11-25-rootline-design.md`: GEN-020 table row `main` and a note below the table (D4); §26 gains row PG-26.
- Overview §5 gains PG-26, §6 gains the PG-26 traceability row. The next free ADR number is 0046.
- The W1-T14 implementer, on `feat/w1-ci`: replaces `scripts/ci_changed_files.py` with the D2 interface; adds `tests/repo/test_ci_changed_files.py`; adds `with: {version: "v${{ env.V_TRIVY }}"}` to the trivy step (merged into the existing `with`) and `GITLEAKS_VERSION` to the gitleaks step `env`; keeps `name: ci / required`, the five `setup-uv` versions and the rulesets of `8b2ce1c`, which already match D3 to D5 apart from trivy and gitleaks; rebases onto the `develop` commit that contains this ADR, so `check_ownership.py` reads the new `owns`.
- `wiki/adr/0025-branching.md` gains the amendment section; `wiki/index.md` lists this ADR.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| (D1) No test for `ci_changed_files.py` | WIK-020 enforcement in CI would rest on untested code |
| (D1) Put the test in an always-allowed path | Overview §7.4 always-allowed paths are shared files; a task's own test belongs in its `owns` |
| (D2) Let every failure raise and rely on Python's traceback | Exit 1 with a multi-line trace is indistinguishable from a defect and is not a stable contract |
| (D2) Use exit 1 for failures | `scripts/check_ownership.py` and `scripts/check_versions.py` already use exit 2 for "could not run" (PG-21, PG-22); one convention is simpler |
| (D2) Add `--end-of-options` before the revision range | Changes the PG-21 command shared with `check_ownership.py`; CI passes fixed refs that never start with `-` |
| (D3) Change the ruleset context to `required` | GEN-020 names `ci / required`; changing the job name keeps the spec text and is one line |
| (D4) Keep `required_linear_history` and release by squash | Contradicts GEN-021, which the owner approved; squashing loses the per-PR history on `main` |
| (D4) Keep `required_linear_history` and let the owner bypass it for each release | Every release would rely on the bypass, which hides real violations and makes the rule meaningless |
| (D5) `uv python install ${{ env.V_PYTHON }}` in all five uv jobs | Adds a download step to four jobs for no test that depends on the patch version; costs minutes (CI-002) |
| (D5) Leave trivy and gitleaks at the action defaults | Contradicts GEN-050: the version would change when the action release changes, not when `versions.yaml` changes |
| (D6) Let W1-T14 edit `wiki/versions.md` | The file is owned by W1-T02 (PG-22); W1-T14 is in a parallel stage and would fail G1 |
| (D6) Record SHAs in `versions.yaml` | Adds a schema change to W1-T02 code (`versions_lib.validate`) for values that only `ci.yml` uses |

## Spec references

CI-001, CI-002, GEN-020, GEN-021, GEN-050, GEN-051, SEC-081, SEC-083, WIK-020, PG-21, PG-22, PG-26, O-3, spec §0.3, §4.3, §17.1, §26, overview §5, §6, §7.3, §7.4, §7.7, W1-T02 Step 8, W1-T14.
