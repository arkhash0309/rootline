# 0038 — Ruff excludes Markdown; plan code blocks fix content, not formatting (spec-gap)

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-19 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

CI-001 requires `ruff format --check` in the `python` job of `ci.yml`. The same command, `uv run ruff format --check .`, runs in `scripts/lint.py` (`task lint`, W1-T06) and in integration-gate check G5 (overview §7.7). The spec does not say which files the check covers.

The W1-T01 review found two failures on `develop` at `4898699`:

1. `tests/repo/test_layout.py` was copied character for character from the W1-T01 Step 1 code block, and that block was not `ruff format` output, so the committed file fails the check.
2. ruff `0.17.6` (the version in `uv.lock`) also formats fenced `python` code blocks inside Markdown files. `uv run ruff format --check .` therefore fails on `docs/superpowers/specs/2026-11-25-rootline-design.md` and on the plan files for weeks 1 to 4, whose code blocks are documentation written for readability (aligned comments, compact lists), not source files.

A one-time `uv run ruff format .` step in W1-T14 was considered. W1-T14 runs in the parallel stage W1-P3 and owns only `.github/workflows/ci.yml`, `.github/rulesets/**`, `scripts/ci_changed_files.py` and `wiki/runbooks/github-apps.md` (schedule YAML). A repository-wide reformat there would change files owned by W1-T09, W1-T10 and W1-T11 in the same stage and by W1-T01, would fail gate check G1 (ownership), and would rewrite the owner-approved spec's code blocks.

## Decision

1. The root `pyproject.toml` `[tool.ruff]` table gets `extend-exclude = ["*.md"]`, directly after `target-version = "py312"`. The pattern matches the file name, so every `*.md` file in every directory is excluded from both `ruff check` and `ruff format`. Verified on 2026-11-26 with ruff `0.17.6`: with this setting, `uv run ruff format --check .` checks the 14 Python files on `develop` and reports only `tests/repo/test_layout.py`.
2. Plan code blocks fix a file's content, not its formatting. Before every commit that adds or changes `*.py` files, the implementer runs `uv run ruff format <each added or changed .py file>` and then `uv run ruff check <the same files>`, which must exit 0. A committed file that differs from its plan block only in what `ruff format` changes complies with the plan, and reviewers do not flag those differences (overview Global Constraints "Formatting").
3. The W1-T01 Step 1 `tests/repo/test_layout.py` block is replaced by its `ruff format` output (with the PG-18 additions of ADR 0037).
4. W1-T16 Step 0 applies decisions 1 and 3 to the committed files in one commit in the W1-T16 PR: `pyproject.toml` and `tests/repo/test_layout.py`, nothing else. W1-T16 runs in the sequential stage W1-S2, so the ownership check allows both files and the schedule YAML does not change.
5. W1-T14 keeps `uv run ruff format --check .` exactly as planned and adds no format step.

This follows spec §0.3: one configuration line and a per-commit habit are simpler and cheaper than reformatting the spec and four plan files (about 1,800 changed lines), and safer, because the owner-approved spec text stays as approved.

## Consequences

- `ci.yml`, `task lint` and G5 all pass the format check on documentation without per-command flags, because the exclusion lives in the one ruff configuration they share.
- Python code blocks in Markdown are never checked by ruff. Their correctness is checked when an implementer writes them to a `*.py` file, formats it, and runs the tests.
- Every implementer commit runs ruff on the files it touches, so a format failure in CI points to the task that last changed the file (overview §7.8).
- If a ruff version newer than `0.17.6` changes Markdown handling, the exclusion still applies, because it is a file-pattern exclusion, not a Markdown-specific setting.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| One-time `uv run ruff format .` in W1-T14 | Not executable as written: W1-T14 is in parallel stage W1-P3 and does not own the affected files (overview §7.4, gate check G1); it would also rewrite the spec's code blocks |
| Reformat all Markdown code blocks with `uv run ruff format docs` and keep Markdown in scope | About 1,800 changed lines in the approved spec and plans; aligned comments in interface listings become harder to read; every plan edit after that would also have to be ruff-formatted |
| Pass `--exclude` on each command line (`ci.yml`, `scripts/lint.py`, G5) | Three places to keep in sync instead of one configuration line |
| Reformat `tests/repo/test_layout.py` in a commit of W1-T16 without changing the plan | The plan block and the committed file would differ, and the next agent copying the block would reintroduce the failure |

## Spec references

CI-001, GEN-001, GEN-002, PG-19, overview Global Constraints "Formatting", overview §7.4, §7.7 (G1, G5), W1-T01 Step 1 and Step 3, W1-T06 (`scripts/lint.py`), W1-T14, W1-T16 Step 0, spec §0.3, spec §26.
