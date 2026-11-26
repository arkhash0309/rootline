# Rootline Implementation Plan — Week 1: Foundations

> **For agentic workers:** Execute this week with the swarm protocol in `2026-11-26-rootline-00-overview.md` §7: the Haiku 5.5 coordinator runs the stages in the **Execution schedule** below, dispatching Sonnet 5.5 implementers (high effort, one worktree per task in parallel stages), Opus 5.5 reviewers (high effort) and, when re-planning is needed, the Opus 5.5 planner (high effort) — `CLAUDE.md` → "Agent models and roles". Within each task, follow superpowers:subagent-driven-development's discipline (implement → spec-compliance review → code-quality review). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reproducible repository, wiki, toolchain and local k3d platform (ArgoCD, cert-manager, ESO, CNPG Postgres, observability, the trimmed workload) that passes `task doctor`, the WKL-004 baseline gate and CI.

**Architecture:** One uv workspace and one Taskfile drive everything. ArgoCD runs an app-of-apps Helm chart (`deploy/root`) whose Applications deploy upstream charts and small Rootline charts in sync waves. The workload is rendered once to plain YAML in the separate `rootline-env` repository.

**Tech Stack:** uv, Python 3.12, go-task, Helm 3, k3d/k3s, ArgoCD 3.x, cert-manager, External Secrets Operator, CloudNativePG, kube-prometheus-stack, Loki, Tempo, OpenTelemetry Collector, GitHub Actions.

## Global Constraints

All constraints in `2026-11-26-rootline-00-overview.md` → "Global Constraints" apply. Week-specific additions:

- Nothing in this week calls a paid API.
- No Rootline service images exist yet, except where a task says so. The umbrella chart `deploy/charts/rootline` is created empty (W1-T10) and gains components in later weeks.
- Week 1 acceptance (MS-001): `task up` healthy; `task doctor` OK; WKL-004 baseline gate passed; S2 memory ≤ 9.5 GiB measured; `task wiki:lint` passes; `ci.yml` green.


## Execution schedule

Mirrors `2026-11-26-rootline-schedule.yaml` (week 1); `uv run python scripts/swarm_schedule.py table --week 1` must print exactly this table. Parallel stages run in separate worktrees (at most 3 implementers at once), then pass the integration gate (overview §7.6–§7.7) before one squash-merged PR reaches `develop`. Owned paths per task are listed in the YAML only. Deferred steps (overview §7.3) run at the start of the named sequential stage.

| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |
|---|---|---|---|---|
| W1-S1 | sequential | — | W1-T01 (`feat/w1-repo-skeleton`) | — |
| W1-S2 | sequential | W1-S1 | W1-T16 (`feat/w1-swarm-tooling`); W1-T08 (`docs/w1-env-repo`) | — |
| W1-P1 | parallel | W1-S2 | W1-T02 (`feat/w1-versions`); W1-T03+W1-T04 (`feat/w1-wiki`) | W1-T02 steps 8 → W1-S3 |
| W1-P2 | parallel | W1-P1 | W1-T05 (`feat/w1-wiki-skill`); W1-T06 (`feat/w1-taskfile`); W1-T07 (`feat/w1-py-common`) | W1-T05 steps 4 → W1-S3; W1-T05 pre-dispatch steps 1 (coordinator) |
| W1-P3 | parallel | W1-P2 | W1-T09 (`feat/w1-workload-render`); W1-T10 (`feat/w1-gitops-root`); W1-T11 (`feat/w1-observability-postgres`); W1-T14 (`feat/w1-ci`) | W1-T09 steps 6, 7 → W1-S3; W1-T14 steps 2, 3 → W1-S3 |
| W1-S3 | sequential | W1-P3 | W1-T12 (`feat/w1-task-up`); W1-T13 (`feat/w1-baseline-gate`); W1-T15 (no branch) | — |

---

### Task W1-T01: Repository skeleton and uv workspace

**Requirement IDs:** GEN-001, GEN-002, GEN-003, GEN-022, GEN-023, WIK-031, PG-8.
**Depends on:** nothing. **Branch:** `feat/w1-repo-skeleton`.

> **Amended 2026-11-26 after W1-T01 was merged (`develop` at `4898699`), per PG-18, PG-19 and PG-20 (overview §5; ADRs 0037, 0038, 0039).** Four code blocks of this task changed after the merge: (1) the `tests/repo/test_layout.py` block in Step 1 is now the `ruff format` output of the original block and its `ALLOWED_TOP_LEVEL` set gains `".hypothesis"`, `".coverage"`, `"coverage.xml"`, `"htmlcov"` and `".swarm"`; (2) the `[tool.ruff]` table in Step 3 gains `extend-exclude = ["*.md"]`; (3) the Step 9 trailer is the implementer trailer of overview §7.1; (4) the trailer bullet of the Step 7 block is the owner-approved per-role bullet (PG-20, ADR 0039). The files committed in `4898699` still have the original content. Item (4) is already applied to `CLAUDE.md` and `AGENTS.md` by branch `docs/w1-plan-gaps`, so W1-T16 Step 0 does not touch those two files. **W1-T16 Step 0** brings `tests/repo/test_layout.py` and `pyproject.toml` in line with these blocks in one commit; W1-T01 is not re-run. The committed history is not rewritten.

**Files:**
- Create: `pyproject.toml` (workspace root), `uv.lock` (generated)
- Create: `libs/py-common/pyproject.toml`, `libs/py-common/rootline_common/__init__.py`
- Create: `libs/py-mcpkit/pyproject.toml`, `libs/py-mcpkit/rootline_mcpkit/__init__.py`
- Create: `libs/py-llm/pyproject.toml`, `libs/py-llm/rootline_llm/__init__.py`
- Create: `libs/py-schemas/pyproject.toml`, `libs/py-schemas/rootline_schemas/__init__.py`
- Create: `services/{api,agent,gate,faultlab,mcp-k8s,mcp-telemetry,mcp-gitops}/pyproject.toml` and the matching `rootline_<name>/__init__.py`
- Create: `eval/runner/pyproject.toml`, `eval/runner/rootline_eval/__init__.py`
- Create: empty-directory markers `.gitkeep` in `apps/console/`, `policies/opa/`, `policies/kyverno/`, `prompts/`, `eval/baselines/`, `eval/reports/`, `deploy/root/`, `deploy/charts/rootline/`, `deploy/values/`, `deploy/upstream/`, `infra/terraform/persistent/`, `infra/terraform/cluster/`, `infra/k3d/`, `scripts/`, `docs/writeup/`, `wiki/`, `.claude/skills/rootline-wiki/`
- Create: `LICENSE`, `.github/pull_request_template.md`, `AGENTS.md`
- Modify: `CLAUDE.md` (add the WIK-031 sections above the existing documentation rule)
- Modify: `.gitignore` (add `eval/runs/`, `data/`, `infra/terraform/**/backend_override.tf`, `infra/terraform/**/terraform.tfvars`, `.venv/`)
- Test: `tests/repo/test_layout.py`, `tests/repo/conftest.py`

**Interfaces:**
- Produces: the 12 importable packages named in GEN-002; the root dev dependency group used by every later task; `tests/repo/` for repository-level tests (PG-8).

- [ ] **Step 1: Write the failing layout test**

`tests/repo/conftest.py`:

```python
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def repo() -> Path:
    return REPO
```

`tests/repo/test_layout.py`:

```python
"""Verifies GEN-001, GEN-002, GEN-003, WIK-031."""

import importlib
import tomllib
from pathlib import Path

import pytest

DIRS = [
    ".claude/skills/rootline-wiki",
    ".github",
    "apps/console",
    "services/api",
    "services/agent",
    "services/gate",
    "services/faultlab",
    "services/mcp-k8s",
    "services/mcp-telemetry",
    "services/mcp-gitops",
    "libs/py-common",
    "libs/py-mcpkit",
    "libs/py-llm",
    "libs/py-schemas",
    "policies/opa",
    "policies/kyverno",
    "prompts",
    "eval/runner",
    "eval/baselines",
    "eval/reports",
    "deploy/root",
    "deploy/charts/rootline",
    "deploy/values",
    "deploy/upstream",
    "infra/terraform/persistent",
    "infra/terraform/cluster",
    "infra/k3d",
    "scripts",
    "docs/superpowers/specs",
    "docs/superpowers/plans",
    "docs/writeup",
    "wiki",
]
PACKAGES = [
    "rootline_api",
    "rootline_agent",
    "rootline_gate",
    "rootline_faultlab",
    "rootline_mcp_k8s",
    "rootline_mcp_telemetry",
    "rootline_mcp_gitops",
    "rootline_common",
    "rootline_mcpkit",
    "rootline_llm",
    "rootline_schemas",
    "rootline_eval",
]
ALLOWED_TOP_LEVEL = {
    ".claude",
    ".github",
    "apps",
    "services",
    "libs",
    "policies",
    "prompts",
    "eval",
    "deploy",
    "infra",
    "scripts",
    "docs",
    "wiki",
    "tests",
    "Taskfile.yml",
    "pyproject.toml",
    "uv.lock",
    "versions.yaml",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "LICENSE",
    ".gitignore",
    ".gitattributes",
    ".env.example",
    ".git",
    ".venv",
    ".omc",
    ".superpowers",
    ".env.local",
    ".env.gke",
    "data",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    ".coverage",
    "coverage.xml",
    "htmlcov",
    ".swarm",
}


@pytest.mark.parametrize("d", DIRS)
def test_directory_exists(repo: Path, d: str) -> None:
    assert (repo / d).is_dir(), d


def test_no_unexpected_top_level_entries(repo: Path) -> None:
    extra = {p.name for p in repo.iterdir()} - ALLOWED_TOP_LEVEL
    assert extra == set(), f"new top-level entries need an ADR: {sorted(extra)}"


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_importable(pkg: str) -> None:
    importlib.import_module(pkg)


def test_workspace_members(repo: Path) -> None:
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["uv"]["workspace"]["members"] == ["libs/*", "services/*", "eval/runner"]


def test_license_is_mit_with_holder(repo: Path) -> None:
    text = (repo / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Aadhavan Arkhash Saravanakumar" in text


@pytest.mark.parametrize("name", ["AGENTS.md", "CLAUDE.md"])
def test_agent_instruction_files(repo: Path, name: str) -> None:
    text = (repo / name).read_text(encoding="utf-8")
    assert "load the `rootline-wiki` skill" in text
    assert "docs/superpowers/specs/2026-11-25-rootline-design.md" in text
    assert "wiki/index.md" in text
    assert "feat/<slug>" in text
    assert "Co-Authored-By:" in text
    assert "Documentation rule" in text
    assert "Agent models and roles" in text
    for model in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"):
        assert model in text


def test_pr_template_headings(repo: Path) -> None:
    text = (repo / ".github/pull_request_template.md").read_text(encoding="utf-8")
    for h in [
        "## Summary",
        "## Requirement IDs",
        "## Wiki pages updated",
        "## Tests",
        "## Screenshots (UI only)",
        "## Cost impact",
    ]:
        assert h in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pytest pytest tests/repo/test_layout.py -v`
Expected: FAIL (missing directories, `pyproject.toml` not found).

- [ ] **Step 3: Create the workspace root `pyproject.toml`**

```toml
[project]
name = "rootline-workspace"
version = "0.1.0"
description = "Rootline uv workspace root (not published)"
requires-python = ">=3.12,<3.13"
dependencies = [
  "rootline-common", "rootline-mcpkit", "rootline-llm", "rootline-schemas",
  "rootline-api", "rootline-agent", "rootline-gate", "rootline-faultlab",
  "rootline-mcp-k8s", "rootline-mcp-telemetry", "rootline-mcp-gitops", "rootline-eval",
]

[tool.uv]
package = false

[tool.uv.workspace]
members = ["libs/*", "services/*", "eval/runner"]

[tool.uv.sources]
rootline-common = { workspace = true }
rootline-mcpkit = { workspace = true }
rootline-llm = { workspace = true }
rootline-schemas = { workspace = true }
rootline-api = { workspace = true }
rootline-agent = { workspace = true }
rootline-gate = { workspace = true }
rootline-faultlab = { workspace = true }
rootline-mcp-k8s = { workspace = true }
rootline-mcp-telemetry = { workspace = true }
rootline-mcp-gitops = { workspace = true }
rootline-eval = { workspace = true }

[dependency-groups]
dev = [
  "pytest>=8,<9", "pytest-asyncio>=1,<2", "pytest-cov>=6,<8", "hypothesis>=6,<7",
  "respx>=0.22,<1", "ruff>=0.14,<1", "mypy>=1.18,<2", "testcontainers[postgres]>=4,<5",
  "pyyaml>=6,<7", "types-pyyaml",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"
markers = [
  "integration: needs Docker (testcontainers)",
  "k8s: needs a kind or k3d cluster (task test:k8s)",
  "integration_contract: cross-task contract test; deselected inside parallel worktrees, run by the integration gate (overview §7.7 G6)",
]

[tool.ruff]
line-length = 110
target-version = "py312"
extend-exclude = ["*.md"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "S", "ASYNC", "RUF"]
ignore = ["S101"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

`extend-exclude = ["*.md"]` (PG-19, ADR 0038): ruff `0.17.6` (the version in `uv.lock` at `4898699`) formats fenced `python` code blocks inside Markdown files, so `uv run ruff format --check .` would otherwise fail on the spec and the plan files, whose code blocks are documentation, not source. The pattern matches the file name, so it excludes every `*.md` file in every directory, for both `ruff check` and `ruff format`.

The dependency line constraints above are placeholders for the *lines* only; W1-T02 adjusts every constraint so it admits the version resolved into `versions.yaml`, and `uv.lock` pins the exact version.

- [ ] **Step 4: Create the 12 member packages**

Each member `pyproject.toml` follows this exact pattern (shown for `libs/py-common`; replace name, description and package directory):

```toml
[project]
name = "rootline-common"
version = "0.1.0"
description = "Shared config, logging, ULIDs, auth, audit and problem+json helpers"
requires-python = ">=3.12,<3.13"
dependencies = []

[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["rootline_common"]
```

| Directory | `name` | Package dir | `description` |
|---|---|---|---|
| `libs/py-common` | `rootline-common` | `rootline_common` | as above |
| `libs/py-mcpkit` | `rootline-mcpkit` | `rootline_mcpkit` | Shared MCP server scaffolding: auth, redaction, replay |
| `libs/py-llm` | `rootline-llm` | `rootline_llm` | In-house LLM access layer (AGT-060) |
| `libs/py-schemas` | `rootline-schemas` | `rootline_schemas` | Pydantic models shared across services |
| `services/api` | `rootline-api` | `rootline_api` | Platform API (FastAPI) |
| `services/agent` | `rootline-agent` | `rootline_agent` | LangGraph investigation workers |
| `services/gate` | `rootline-gate` | `rootline_gate` | Policy gate: OPA, approvals, merge, sync, verify |
| `services/faultlab` | `rootline-faultlab` | `rootline_faultlab` | Fault injection and snapshot capture |
| `services/mcp-k8s` | `rootline-mcp-k8s` | `rootline_mcp_k8s` | MCP server rootline-k8s |
| `services/mcp-telemetry` | `rootline-mcp-telemetry` | `rootline_mcp_telemetry` | MCP server rootline-telemetry |
| `services/mcp-gitops` | `rootline-mcp-gitops` | `rootline_mcp_gitops` | MCP server rootline-gitops |
| `eval/runner` | `rootline-eval` | `rootline_eval` | rootline-eval CLI |

Each `rootline_<x>/__init__.py` contains exactly:

```python
"""<description from the table>."""

__version__ = "0.1.0"
```

Create a `.gitkeep` (empty file) in every directory from the **Files** list that would otherwise be empty.

- [ ] **Step 5: Create `LICENSE`**

Standard MIT text, first line `MIT License`, then a blank line, then `Copyright (c) 2026 Aadhavan Arkhash Saravanakumar`, then the standard MIT permission and warranty paragraphs verbatim from https://opensource.org/license/mit.

- [ ] **Step 6: Create `.github/pull_request_template.md`**

```markdown
## Summary
<!-- What changed and why, in 1–5 sentences. -->

## Requirement IDs
<!-- Spec IDs implemented or affected, e.g. LAB-030, TST-LAB-001. Plan task ID, e.g. W2-T06. -->

## Wiki pages updated
<!-- List of wiki/ files changed, or the line `wiki-skip: <reason>`. -->

## Tests
<!-- Commands run and their result. -->

## Screenshots (UI only)

## Cost impact
<!-- USD spent on LLM or cloud for this PR, and expected recurring cost. "None" if none. -->
```

- [ ] **Step 7: Write `AGENTS.md` and update `CLAUDE.md`**

Both files start with this block (identical text). In `CLAUDE.md` it goes directly under the `# CLAUDE.md — Rootline` heading and introduction, *above* the existing "Agent models and roles" and "Documentation rule" sections, which stay unchanged. `AGENTS.md` contains this block, then a verbatim copy of the `CLAUDE.md` section "Agent models and roles (owner instruction, 2026-11-26 — mandatory)", then the line `The documentation rule in CLAUDE.md ("Documentation rule") applies to every document you write.`

```markdown
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

- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, `build:`, `perf:`, with optional scope = component directory name, e.g. `feat(agent): add verify node`.
- Commits end with the trailer for your role in `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §7.1, "Commit attribution trailers" (implementer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, planner `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, coordinator `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`).
```

This block is identical to the "Commit rules (GEN-022)" section of `CLAUDE.md` and `AGENTS.md` on `develop`. Its trailer bullet was approved by the owner on 2026-11-26 (overview §5 PG-20, ADR 0039) and committed on branch `docs/w1-plan-gaps`; the files in `4898699` still carry the earlier bullet "Commits authored by AI agents end with the attribution trailer in use in the session, currently: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`", and that commit is not rewritten. The bullet repeats the table in overview §7.1 "Commit attribution trailers (GEN-022, PG-20)"; if the two ever differ, the §7.1 table decides. The Conventional Commits bullet of this block does not list `revert:`; GEN-022 allows it (owner decision 2026-11-26, ADR 0039), and the coordinator's revert commits (overview §7.1, §7.8) use it.

- [ ] **Step 8: Sync and run the tests**

Run: `uv sync --all-packages` then `uv run pytest tests/repo/test_layout.py -v`
Expected: all PASS. `uv.lock` is created.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "build: add repository skeleton and uv workspace

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task W1-T16: Swarm and integration tooling

**Requirement IDs:** PG-16 (overview §7), PG-18, PG-19, PG-20, GEN-001, GEN-022, CI-001, GEN-041, WIK-020, TST-002, TST-010.
**Depends on:** W1-T01. Runs in stage W1-S2, before every parallel stage (schedule `W1-S2`). **Branch:** `feat/w1-swarm-tooling`.

**Files:**
- Modify (Step 0, its own commit): `tests/repo/test_layout.py` (replace with the W1-T01 Step 1 block), `pyproject.toml` (add `extend-exclude = ["*.md"]` to `[tool.ruff]`)
- Create: `scripts/proc.py` (moved here from W1-T06), `scripts/swarm_schedule.py`, `scripts/check_ownership.py`, `scripts/integration_gate.py`, `scripts/cluster_smoke.py`, `scripts/swarm_lib.py`
- Create: `tests/registry/README.md`, `tests/smoke/README.md`, `tests/registry/schema.json`, `tests/smoke/schema.json`
- Modify: `.gitattributes` (add `wiki/log.md merge=union`), `.gitignore` (add `.swarm/`, `.hypothesis/`, `coverage.xml`)
- Test: `tests/repo/test_swarm_schedule.py`, `tests/repo/test_check_ownership.py`, `tests/repo/test_integration_gate.py`, `tests/repo/test_cluster_smoke.py`

W1-T16 is in a sequential stage, so the schedule gives it no `owns` list and `scripts/check_ownership.py` passes it for every path (overview §7.4, W1-T16 Step 3). Changing `tests/repo/test_layout.py`, a W1-T01 file, is therefore allowed here and needs no schedule change.

**Interfaces:**
- `scripts.proc.run(cmd, *, check=True, capture=True, env=None, timeout=600, input_text=None) -> CompletedProcess[str]` (exact code in W1-T06 step 2; W1-T06 now imports it instead of creating it).
- `scripts.swarm_lib.load_schedule(path=REPO/"docs/superpowers/plans/2026-11-26-rootline-schedule.yaml") -> Schedule`; dataclasses `Schedule(version, max_parallel_implementers, always_allowed: list[str], weeks: list[Week])`, `Week(week, stages: list[Stage])`, `Stage(id, mode, after, tasks: list[TaskEntry])`, `TaskEntry(id, branch, combined_with, owns, excludes, pre_steps, deferred_steps, deferred_to)`; `matches(path: str, globs: list[str]) -> bool` (gitignore-style via `pathspec`, add `pathspec` to `versions.yaml` and the root dev group).
- CLI `uv run python scripts/swarm_schedule.py validate | next --week N | done <stage> | show <stage> | table --week N`; progress file `.swarm/progress.json` = `{"done": [stage ids], "stage_bases": {stage: sha}}`.
- CLI `uv run python scripts/check_ownership.py --task <id> --base <sha> [--branch <ref>]` → exit 0, or exit 1 with one line per offending path `ownership: <path> not owned by <task>`.
- CLI `uv run python scripts/integration_gate.py --stage <id> [--branch <ref>] [--base origin/develop] [--pr-body <file>] [--report-only]` → checks G1–G11 of overview §7.7 (G12 is `cluster_smoke.py`), report `.swarm/gates/<stage>.json`, exit 1 on any `fail` (exit 0 with `--report-only`).
- CLI `uv run python scripts/cluster_smoke.py [--context k3d-rootline] [--timeout 1200]` → G12.

- [ ] **Step 0: Fix the W1-T01 review findings (PG-18, PG-19; ADRs 0037, 0038) in one commit**

Before Step 1, on `feat/w1-swarm-tooling` (branched from the `develop` tip, which contains `4898699` and this plan amendment). This is a separate commit so the reviewer can check it apart from the tooling.

0. Precondition (no worktree checkouts under `.swarm/`): run `git worktree list --porcelain`. If any line that starts with `worktree ` names a path under `/home/arkhash0309/projects/rootline/.swarm/worktrees/`, stop and report `BLOCKED` with those lines; do not run steps 1 to 6. Reason: `.swarm/` is not in `.gitignore` until Step 7, so ruff would also check the Python files inside those worktree checkouts and the step 2 and step 5 counts would not hold. The coordinator then removes each listed worktree with `git worktree remove <path>`, runs `git worktree prune`, and re-dispatches this step. If no line names such a path, continue with step 1. The `.gitignore` change stays in Step 7.
1. Run `uv run pytest tests/repo/test_layout.py -v`. Expected on `4898699`: `test_no_unexpected_top_level_entries` FAILS with `new top-level entries need an ADR: ['.swarm']` when the coordinator's `.swarm/` directory exists in the checkout. If `.swarm/` does not exist in the checkout, the test passes; continue anyway.
2. Run `uv run ruff format --check .`. Expected before this step: exit 1; ruff `0.17.6` prints one `unformatted: File would be reformatted` entry per file, each followed by a `--> <path>:<line>:<col>` line, for these six files: `tests/repo/test_layout.py`, `docs/superpowers/specs/2026-11-25-rootline-design.md`, `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`, `docs/superpowers/plans/2026-11-26-rootline-w2-fault-lab.md`, `docs/superpowers/plans/2026-11-26-rootline-w3-identity-mcp.md` and `docs/superpowers/plans/2026-11-26-rootline-w4-agent-mvp.md` (the spec and the plan files contain unformatted `python` code blocks), and ends with the line `6 files would be reformatted, 28 files already formatted` (verified on `ec2a811`). A different count does not block this step when step 0 passed; record the printed last line in the PR description and continue.
3. Replace the whole content of `tests/repo/test_layout.py` with the W1-T01 Step 1 `tests/repo/test_layout.py` block, character for character. Do not edit `tests/repo/conftest.py`.
4. In the root `pyproject.toml`, add the line `extend-exclude = ["*.md"]` directly after `target-version = "py312"` in `[tool.ruff]`. Change nothing else in the file. `uv.lock` does not change (ruff settings are not dependencies). If `uv lock --check` reports a change, stop and report `BLOCKED`.
5. Run, in this order, and require each result:

| Command | Required result |
|---|---|
| `uv run ruff format --check .` | exit 0; the last line is `14 files already formatted` (12 package `__init__.py` files, `tests/repo/conftest.py`, `tests/repo/test_layout.py`) |
| `uv run ruff check .` | exit 0, `All checks passed!` |
| `uv run pytest tests/repo -v` | exit 0; 50 tests pass on `4898699` plus this commit |
| `git diff --stat HEAD` | exactly two files changed: `pyproject.toml`, `tests/repo/test_layout.py` |

If `uv run ruff format --check .` still lists a file, the only allowed fix is `uv run ruff format <that file>` when the file is `tests/repo/test_layout.py`; for any other file stop and report `BLOCKED` with the listing.

6. Commit:

```bash
git add pyproject.toml tests/repo/test_layout.py
git commit -m "chore: ruff-format layout test, allow .swarm and tool outputs, exclude Markdown from ruff

Implements PG-18 (ADR 0037) and PG-19 (ADR 0038) from the W1-T01 review.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 1: Write the failing tests**

`tests/repo/test_swarm_schedule.py`:

```python
"""Verifies PG-16 (overview §7.2 rules)."""
from pathlib import Path

import pytest

from scripts.swarm_lib import load_schedule, matches, validate_schedule

REPO = Path(__file__).resolve().parents[2]


def test_committed_schedule_is_valid() -> None:
    assert validate_schedule(load_schedule()) == []


def test_every_plan_task_scheduled_exactly_once() -> None:
    import re
    plans = "".join(p.read_text(encoding="utf-8") for p in (REPO / "docs/superpowers/plans").glob("*-w*.md"))
    defined = set(re.findall(r"^### Task (W\d-T\d\d):", plans, re.M))
    sched = load_schedule()
    scheduled = [t.id for w in sched.weeks for s in w.stages for t in s.tasks]
    combined = [c for w in sched.weeks for s in w.stages for t in s.tasks for c in t.combined_with]
    assert sorted(scheduled + combined) == sorted(defined)
    assert len(scheduled + combined) == len(set(scheduled + combined))


def test_rules_detected(tmp_path: Path) -> None:
    bad = tmp_path / "s.yaml"
    bad.write_text("""
version: 1
max_parallel_implementers: 3
always_allowed: [wiki/log.md]
weeks:
  - week: 9
    stages:
      - id: W9-P1
        mode: parallel
        after: [W9-X]
        tasks:
          - {id: W9-T01, branch: feat/a, owns: [a/**, services/api/migrations/versions/0009_x.py]}
          - {id: W9-T02, branch: feat/b, owns: [a/b.py, services/api/migrations/versions/0010_y.py], deferred_steps: [2]}
""", encoding="utf-8")
    errors = validate_schedule(load_schedule(bad))
    assert "W9-P1: unknown stage in after: W9-X" in errors
    assert "W9-P1: W9-T01 and W9-T02 both own a/b.py" in errors
    assert "W9-P1: two tasks add Alembic revisions" in errors
    assert "W9-P1: W9-T02 has deferred_steps but no deferred_to" in errors


def test_matches_gitignore_style() -> None:
    assert matches("services/api/x/y.py", ["services/api/**"])
    assert matches("apps/console/app/(app)/lab/page.tsx", ["apps/console/app/(app)/lab/**"])
    assert not matches("services/apix/y.py", ["services/api/**"])
```

`validate_schedule` rules (each produces exactly the error string format shown): stage IDs unique and match `^W\d-[SP]\d$`; `after` references existing earlier stages; parallel stages: every task has `branch` and non-empty `owns`; no path owned by two tasks of the same parallel stage — detected by checking each task's literal (non-glob) owned paths and each glob's fixed prefix against the other tasks' globs; at most one task per parallel stage owns a path under `services/api/migrations/versions/` (message `two tasks add Alembic revisions`); `deferred_steps` non-empty ⇒ `deferred_to` names a sequential stage of the same week that comes later; sequential stages may omit `owns`.

`tests/repo/test_check_ownership.py` (uses a temporary git repo created with `git init` in `tmp_path`, a schedule fixture and two commits): a change inside `owns` passes; a change in `excludes` fails; `wiki/log.md` passes (always-allowed); a non-empty `__init__.py` outside `owns` fails; an empty one passes; a `pyproject.toml` change that touches only `dependencies` passes, one that changes `[project] name` fails (parse both versions with `tomllib` and compare everything except `project.dependencies`, `project.optional-dependencies` and `dependency-groups`); sequential tasks always pass.

`tests/repo/test_integration_gate.py`: with every external command replaced by a fake runner (`integration_gate.run_checks(stage, branch, base, runner=fake)`), assert the checks run in order G1…G11, that a missing tool or input yields `skip` with a reason (for example `G6 console: apps/console/package.json missing`), that one failing check makes the exit code 1, that `--report-only` exits 0, that the JSON report has the overview §7.7 shape, that G8 fails when a registry file present at the base is missing on the branch unless the PR body contains `registry-removal: <id> <reason>`, that G9 fails when the collected test count drops without `test-removal:`, and that G10 is `skip` while `eval/baselines/baseline-smoke.json` does not exist.

`tests/repo/test_cluster_smoke.py`: parses `tests/smoke/*.yaml` fixtures; an `http` check builds the command `kubectl --context <ctx> -n <ns> port-forward svc/<service> <local>:<port>` and requests `http://127.0.0.1:<local><path>`; `exec` and `argocd_app` checks build the expected `kubectl` commands (fake runner); invalid smoke files are rejected against `tests/smoke/schema.json`.

Run: `uv run pytest tests/repo/test_swarm_schedule.py tests/repo/test_check_ownership.py tests/repo/test_integration_gate.py tests/repo/test_cluster_smoke.py -v` → FAIL (modules missing).

- [ ] **Step 2: Implement `scripts/proc.py`** exactly as given in W1-T06 step 2, and `scripts/swarm_lib.py` + `scripts/swarm_schedule.py`. `next --week N` prints the first stage of week N whose `after` stages are all in `progress.done` and which is not itself done; `done <stage>` appends to `progress.done`; `show <stage>` prints the stage's tasks with branch, owns, pre/deferred steps; `table --week N` prints the Markdown "Execution schedule" table used in the wave files (columns `Stage | Mode | After | Tasks (branch) | Deferred steps → stage`), so the wave files can be checked against the YAML.

- [ ] **Step 3: Implement `scripts/check_ownership.py`** — changed files = `git diff --name-only --diff-filter=ACMRD <base>...<branch>`; for a task that is sequential (no `owns`), exit 0; otherwise apply `owns` − `excludes` ∪ `always_allowed` with the pyproject/package.json and `__init__.py` special rules of overview §7.4.

- [ ] **Step 4: Implement `scripts/integration_gate.py`** — each check is a function `(ctx) -> CheckResult(name, status, reason, duration_s, output_tail)` (last 40 lines of output); commands exactly as overview §7.7, run through `scripts.proc.run` with `check=False`; applicability conditions evaluated from files on the branch checkout (the gate checks out `--branch` in a temporary worktree under `.swarm/worktrees/<stage>` with `git worktree add`, runs there, and removes the worktree afterwards, so the coordinator's working tree is never modified). G9 collects counts on the base in a second temporary worktree. PR-body exemptions read from `--pr-body <file>`.

- [ ] **Step 5: Implement `scripts/cluster_smoke.py`** — waits for every ArgoCD Application in `argocd` to be `Synced/Healthy` (poll 15 s, `--timeout` default 1200 s), runs `scripts/doctor.py`'s memory check (≤ 9.5 GiB, imported lazily because `doctor.py` is created by W1-T06; before W1-T06 is merged the memory check is reported `skip`), then every check in `tests/smoke/*.yaml` (`http` checks never follow redirects, so `expect_status` may be a 3xx code); prints one line per check `PASS|FAIL <component>/<name>: <detail>`; exit 1 on any FAIL.

- [ ] **Step 6: Registry and smoke documentation** — `tests/registry/README.md` and `tests/smoke/README.md` state the formats of overview §7.7, the file-naming rule (`<TST-ID>--<task-id>.yaml`, `<component>.yaml`), who creates them (the task that introduces the test or deploys the component), and the exemption lines (`registry-removal:`, `test-removal:`, `baseline-change:`). `schema.json` files are JSON Schema draft 2020-12 for each format.

- [ ] **Step 7: `.gitattributes` and `.gitignore`** — append `wiki/log.md merge=union` to `.gitattributes`; append these three lines, in this order, to the end of `.gitignore` under a comment line `# Swarm state and tool outputs (W1-T16, ADR 0037)`: `.swarm/`, `.hypothesis/`, `coverage.xml`. (`.coverage` and `htmlcov/` are already ignored by the `# Python` block.)

- [ ] **Step 8: Run tests** → PASS; `uv run python scripts/swarm_schedule.py validate` → `schedule OK: 8 weeks, 39 stages, 94 tasks`.

- [ ] **Step 9: Commit**

```bash
git add scripts tests/repo tests/registry tests/smoke .gitattributes .gitignore pyproject.toml uv.lock
git commit -m "build: add swarm schedule, ownership check and integration gate tooling

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

`versions.yaml` does not exist yet at this point (W1-T02 creates it in stage W1-P1); add `pathspec` and `jsonschema` to the root `dev` dependency group with the constraint `>=0` now, and W1-T02 step 6 aligns the constraint with the resolved version (W1-T02's version table gains rows `pathspec` (latest 0.x) and `jsonschema` (4.x)).

---

### Task W1-T02: Resolve and enforce pinned versions

**Requirement IDs:** GEN-050, GEN-051.
**Depends on:** W1-T01. **Branch:** `feat/w1-versions`.

**Files:**
- Create: `versions.yaml`, `scripts/check_versions.py`, `scripts/render_versions.py`, `scripts/versions_lib.py`
- Create (generated, committed): `deploy/root/files/versions.yaml`, `.github/versions.env`
- Create: `wiki/versions.md` (wiki skeleton arrives in W1-T03; create this one page now)
- Test: `tests/repo/test_versions.py`

**Interfaces:**
- Produces: `versions.yaml` schema below; `scripts.versions_lib.load_versions(path: Path = REPO/"versions.yaml") -> dict[str, Any]`; `scripts.versions_lib.version_of(key: str) -> str` (returns the string value, or the `version` field of a mapping); `uv run python scripts/render_versions.py [--check]`.

**`versions.yaml` schema.** Top level is a mapping. Every key of the GEN-050 table is a top-level key with exactly that spelling. A value is either a version string, or a mapping with any of: `version` (string, required in a mapping), `chart` (chart version), `app` (application version), `repo` (Helm repo URL or image repo), `digest` (`sha256:<64 hex>`). Extra keys added during planning are allowed and listed in the table below. A top-level `pin_date: "YYYY-MM-DD"` is required.

| Extra key | Version line | Purpose |
|---|---|---|
| `pydantic-settings` | 2.x | `rootline_common.settings` |
| `python-ulid` | 3.x | ULIDs |
| `pyjwt` | 2.x (`[crypto]`) | JWT validation |
| `cryptography` | latest stable | AES-GCM, RSA |
| `pyyaml` | 6.x | YAML |
| `ruamel-yaml` | 0.18.x or later 0.x | formatting-preserving YAML edits (MCP-040) |
| `duckdb` | 1.x | replay queries |
| `pandas` | 2.x | frames |
| `pyarrow` | latest stable | Parquet |
| `numpy` | 2.x | algorithms |
| `scipy` | 1.x | McNemar binomial test |
| `kubernetes` (Python client) | latest stable | k8s API |
| `jinja2` | 3.x | prompts |
| `uvicorn` | latest stable | ASGI server |
| `prometheus-client` | latest stable | `/metrics` |
| `opentelemetry-sdk` | 1.x (with matching `opentelemetry-instrumentation-*`) | tracing |
| `python-dotenv` | 1.x | reading `.env.local` in scripts |
| `zstandard` | latest stable | `.tar.zst` |
| `matplotlib` | 3.x | report charts |
| `testcontainers` | 4.x | integration tests |
| `gateway-api` | latest standard-channel release 1.x | CRDs (INF-020 wave −4) |
| `kind` | latest 0.x | CI e2e cluster |
| `kubeconform`, `tflint`, `trivy`, `gitleaks`, `kyverno-cli`, `cosign`, `syft` | latest stable | CI tooling |
| `pathspec` | latest 0.x | gitignore-style globs for `scripts/check_ownership.py` (W1-T16) |
| `jsonschema` | 4.x | registry and smoke file validation (W1-T16) |
| `prometheus-operator-crds` | `{version, chart, repo}` latest stable chart | CRDs Application (W1-T10) |
| `postgres-image` | `{version: "16", repo: ghcr.io/cloudnative-pg/postgresql, digest}` | CNPG image (W1-T11) |
| `kubectl-image` | `{version, repo: bitnami/kubectl, digest}` matching the cluster minor | `copy-ca` Job (W1-T10) |
| `busybox` | `{version: "1.37", digest: sha256:…}` | LAB-071 injection Job image |
| `uv-image`, `python-image`, `node-image`, `opa-image` | `{version, repo, digest}` | CI-020 digest-pinned base images |

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies GEN-050."""
import re
from pathlib import Path

import pytest

from scripts.versions_lib import CONSTRAINTS, load_versions, version_of, validate

REPO = Path(__file__).resolve().parents[2]


def test_every_spec_key_present() -> None:
    data = load_versions(REPO / "versions.yaml")
    missing = [k for k in CONSTRAINTS if k not in data]
    assert missing == []


def test_every_value_satisfies_its_line() -> None:
    assert validate(load_versions(REPO / "versions.yaml")) == []


def test_pin_date_format() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", load_versions(REPO / "versions.yaml")["pin_date"])


def test_validate_reports_bad_value() -> None:
    data = {"pin_date": "2026-11-30", "python": "3.11.9"}
    errors = validate(data, keys=["python"])
    assert errors == ["python: '3.11.9' does not match ^3\\.12\\.\\d+$"]


def test_version_of_mapping() -> None:
    assert version_of("x", {"x": {"version": "1.2.3", "digest": "sha256:" + "a" * 64}}) == "1.2.3"


def test_generated_files_up_to_date() -> None:
    import subprocess, sys
    r = subprocess.run([sys.executable, "scripts/render_versions.py", "--check"], cwd=REPO)
    assert r.returncode == 0
```

Add an empty `scripts/__init__.py` so `scripts.versions_lib` imports in tests (the root `pyproject.toml` already makes the repo root importable through `uv run` from the repo root; add `pythonpath = ["."]` to `[tool.pytest.ini_options]`).

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/repo/test_versions.py -v` → FAIL (`ModuleNotFoundError: scripts.versions_lib`).

- [ ] **Step 3: Implement `scripts/versions_lib.py`**

```python
"""Load and validate versions.yaml (GEN-050)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]

# key -> regex the resolved version must fully match (spec GEN-050 table)
CONSTRAINTS: dict[str, str] = {
    "python": r"^3\.12\.\d+$",
    "node": r"^24\.\d+\.\d+$",
    "uv": r"^\d+\.\d+\.\d+$",
    "fastapi": r"^\d+\.\d+\.\d+$",
    "sqlalchemy": r"^2\.0\.\d+$",
    "alembic": r"^1\.\d+\.\d+$",
    "pydantic": r"^2\.\d+\.\d+$",
    "psycopg": r"^3\.\d+\.\d+$",
    "httpx": r"^\d+\.\d+\.\d+$",
    "anthropic": r"^1\.\d+\.\d+$",
    "langgraph": r"^1\.\d+\.\d+$",
    "langgraph-checkpoint-postgres": r"^\d+\.\d+\.\d+$",
    "mcp": r"^\d+\.\d+\.\d+$",
    "langfuse": r"^3\.\d+\.\d+$",
    "drain3": r"^0\.9\.\d+$",
    "ruptures": r"^1\.1\.\d+$",
    "fastembed": r"^\d+\.\d+\.\d+$",
    "pgvector": r"^0\.8\.\d+$",
    "next": r"^16\.\d+\.\d+$",
    "react": r"^19\.\d+\.\d+$",
    "typescript": r"^5\.\d+\.\d+$",
    "tailwindcss": r"^4\.\d+\.\d+$",
    "keycloak": r"^26\.8\.\d+$",
    "keycloak-config-cli": r"^\d+\.\d+\.\d+.*$",
    "argo-cd": r"^3\.\d+\.\d+$",
    "k3d": r"^5\.(8|9|\d{2,})\.\d+$",
    "k3s": r"^v1\.\d+\.\d+\+k3s\d+$",
    "gke": r"^REGULAR$",
    "kube-prometheus-stack": r"^\d+\.\d+\.\d+$",
    "loki": r"^6\.\d+\.\d+$",
    "tempo": r"^\d+\.\d+\.\d+$",
    "opentelemetry-collector": r"^\d+\.\d+\.\d+$",
    "chaos-mesh": r"^2\.(7|8|9|\d{2,})\.\d+$",
    "kyverno": r"^3\.\d+\.\d+$",
    "external-secrets": r"^\d+\.\d+\.\d+$",
    "cert-manager": r"^v?1\.\d+\.\d+$",
    "cloudnative-pg": r"^\d+\.\d+\.\d+$",
    "traefik": r"^3\.\d+\.\d+$",
    "opa": r"^1\.\d+\.\d+$",
    "opentelemetry-demo": r"^0\.42\.8$",
    "terraform": r"^1\.(1[3-9]|[2-9]\d)\.\d+$",
    "google": r"^7\.\d+\.\d+$",
    "ollama": r"^\d+\.\d+\.\d+$",
    "playwright": r"^1\.\d+\.\d+$",
}


def load_versions(path: Path = REPO / "versions.yaml") -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError("versions.yaml must be a mapping")
    return data


def version_of(key: str, data: dict[str, Any] | None = None) -> str:
    data = data if data is not None else load_versions()
    value = data[key]
    if isinstance(value, dict):
        return str(value["version"])
    return str(value)


def validate(data: dict[str, Any], keys: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    for key in keys if keys is not None else list(CONSTRAINTS):
        if key not in data:
            errors.append(f"{key}: missing")
            continue
        v = version_of(key, data)
        pattern = CONSTRAINTS[key]
        if not re.fullmatch(pattern, v):
            errors.append(f"{key}: {v!r} does not match {pattern}")
    for key, value in data.items():
        if isinstance(value, dict) and "digest" in value:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(value["digest"])):
                errors.append(f"{key}: bad digest {value['digest']!r}")
    return errors
```

For mapping values whose GEN-050 constraint is on the *chart* (`argo-cd` app is 3.x but chart has its own version), store `{version: <app version>, chart: <chart version>}`; the regex applies to `version`.

- [ ] **Step 4: Implement `scripts/render_versions.py`**

```python
"""Render files that cannot read versions.yaml directly (GEN-050).

Outputs:
  deploy/root/files/versions.yaml  - subset consumed by the root Helm chart
  .github/versions.env             - KEY=VALUE lines for GitHub Actions ($GITHUB_ENV)
Usage: uv run python scripts/render_versions.py [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from scripts.versions_lib import REPO, load_versions, version_of

CHART_KEYS = [
    "argo-cd", "kube-prometheus-stack", "loki", "tempo", "opentelemetry-collector", "chaos-mesh",
    "kyverno", "external-secrets", "cert-manager", "cloudnative-pg", "traefik", "keycloak",
    "keycloak-config-cli", "gateway-api", "opa-image", "busybox",
]
ENV_KEYS = ["python", "node", "uv", "opa", "terraform", "kind", "kubeconform", "tflint", "trivy",
            "gitleaks", "kyverno-cli", "cosign", "syft", "playwright", "k3s"]


def render() -> dict[Path, str]:
    data = load_versions()
    charts = {k: data[k] for k in CHART_KEYS if k in data}
    out_yaml = "# GENERATED by scripts/render_versions.py from versions.yaml. Do not edit.\n" + yaml.safe_dump(
        charts, sort_keys=True)
    env_lines = ["# GENERATED by scripts/render_versions.py from versions.yaml. Do not edit."]
    for k in ENV_KEYS:
        env_lines.append(f"V_{k.upper().replace('-', '_')}={version_of(k, data)}")
    return {
        REPO / "deploy/root/files/versions.yaml": out_yaml,
        REPO / ".github/versions.env": "\n".join(env_lines) + "\n",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = ap.parse_args()
    stale = []
    for path, content in render().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            if args.check:
                stale.append(str(path.relative_to(REPO)))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        print("stale generated files: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Resolve versions on the pin date and write `versions.yaml`**

Use exactly these lookup methods. Take the newest stable (non-pre-release) version that satisfies the GEN-050 line.

| Kind | Command |
|---|---|
| PyPI package | `uv pip index versions <pkg>` (or `https://pypi.org/pypi/<pkg>/json` → `info.version` when it fits the line) |
| npm package | `npm view <pkg>@<line> version` (e.g. `npm view next@16 version`; take the last line) |
| Helm chart | `helm repo add <name> <url>` then `helm search repo <name>/<chart> --versions` (first row within the line) |
| GitHub release | `gh release list -R <owner/repo> --exclude-pre-releases -L 20` |
| Image digest | `docker buildx imagetools inspect <image>:<tag> --format "{{json .Manifest.Digest}}"` |
| k3s for GKE minor | `gcloud container get-server-config --zone us-central1-a --format="value(channels[channel=REGULAR].defaultVersion)"` gives the GKE minor; pick the newest `rancher/k3s` tag `v1.<minor>.<patch>-k3s<N>` from `gh release list -R k3s-io/k3s`. If `gcloud` has no project yet, use https://cloud.google.com/kubernetes-engine/docs/release-notes-regular and record the source in `wiki/versions.md` |

Helm repositories: `argo https://argoproj.github.io/argo-helm`, `prometheus-community https://prometheus-community.github.io/helm-charts`, `grafana https://grafana.github.io/helm-charts`, `open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts`, `chaos-mesh https://charts.chaos-mesh.org`, `kyverno https://kyverno.github.io/kyverno`, `external-secrets https://charts.external-secrets.io`, `jetstack https://charts.jetstack.io`, `cnpg https://cloudnative-pg.github.io/charts`, `traefik https://traefik.github.io/charts`.

Store chart entries as `{version: <app version>, chart: <chart version>, repo: <repo URL>}`. For `opentelemetry-demo`, the value is exactly `{version: "0.42.8", chart: "0.42.8", app: "3.1.0", repo: "https://open-telemetry.github.io/opentelemetry-helm-charts"}` (the regex applies to `version`, which equals the chart version).

`mcp` rule: pick the newest release whose README or changelog lists protocol revision `2026-07-28`. If none does, pin the newest release, set `mcp_protocol_revision: "2025-11-25"` in `versions.yaml`, and the W1-T04 ADR 0012 records the fallback (GEN-050).

- [ ] **Step 6: Align `pyproject.toml` constraints**

For every Python dependency, set the constraint in the member that uses it to `>=<resolved>,<<next major>>` (for 0.x packages: `>=<resolved>,<0.<minor+1>>`). Run `uv lock` and verify `uv.lock` resolves each to the version in `versions.yaml`: `uv run python -c "import tomllib;print([p['version'] for p in tomllib.load(open('uv.lock','rb'))['package'] if p['name']=='fastapi'])"`.

- [ ] **Step 7: Render and test**

Run: `uv run python scripts/render_versions.py` then `uv run pytest tests/repo/test_versions.py -v` → PASS.

- [ ] **Step 8: Write `wiki/versions.md`** (deferred to stage W1-S3, overview §7.3; W1-T03 creates the page as a stub in the same parallel stage)

Replace the stub's content with: a heading `# Versions`, the line `Pin date: <pin_date>`, a table `| Key | Version | Chart | Source command |` with one row per `versions.yaml` key, and a section `## Upgrade rule` quoting GEN-051.

- [ ] **Step 9: Commit** (made at the end of step 7, per overview §7.3; step 8 commits separately on `feat/w1-versions-deferred`)

```bash
git add versions.yaml scripts/ deploy/root/files/versions.yaml .github/versions.env pyproject.toml uv.lock tests/repo/test_versions.py libs services eval
git commit -m "build: pin versions in versions.yaml and render derived files

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task W1-T03: Wiki skeleton and wiki lint

**Requirement IDs:** WIK-001, WIK-002, WIK-010, WIK-012, WIK-013, WIK-020, WIK-021, GEN-040, CST-012.
**Depends on:** W1-T01. **Parallel-safe** with W1-T02. **Branch:** `feat/w1-wiki`.

**Files:**
- Create: every file in the WIK-002 tree except `wiki/adr/0001…` (W1-T04), `wiki/adr/0037…0039` (already on `develop`, PG-18 … PG-20; do not edit) and `wiki/versions.md` (W1-T02)
- Create: `wiki/components/<slug>.md` for each slug in `COMPONENT_PAGES` below
- Create: `scripts/wiki_lint.py`
- Test: `tests/repo/test_wiki_lint.py`

**Interfaces:**
- Produces: `uv run python scripts/wiki_lint.py [--changed-files <file>] [--pr-body <file>]` exit 0/1, one line per problem `wiki-lint: <rule>: <detail>`; constant `COMPONENT_PAGES`.

`COMPONENT_PAGES` (one file each in `wiki/components/`): `console`, `api`, `agent`, `gate`, `faultlab`, `mcp-telemetry`, `mcp-k8s`, `mcp-gitops`, `migrate`, `demo-seed`, `postgres`, `keycloak`, `keycloak-config`, `otel-collector`, `kube-prometheus-stack`, `loki`, `tempo`, `argocd`, `chaos-mesh`, `kyverno`, `external-secrets`, `cert-manager`, `traefik`, `workload`, plus the extra pages `telemetry`, `capacity`.

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies WIK-020, WIK-021."""
import subprocess
from datetime import date
from pathlib import Path

import pytest

from scripts import wiki_lint as wl


def make_wiki(root: Path) -> Path:
    w = root / "wiki"
    (w / "adr").mkdir(parents=True)
    (w / "components").mkdir()
    for n in range(1, 26):
        (w / "adr" / f"{n:04d}-x.md").write_text("# ADR\n", encoding="utf-8")
    (w / "adr" / "0000-template.md").write_text("# T\n", encoding="utf-8")
    for slug in wl.COMPONENT_PAGES:
        (w / "components" / f"{slug}.md").write_text("# C\n", encoding="utf-8")
    files = sorted(p.relative_to(w).as_posix() for p in w.rglob("*.md"))
    index = "# Index\n" + "".join(f"- [{f}]({f})\n" for f in files + ["index.md", "status.md"])
    (w / "index.md").write_text(index, encoding="utf-8")
    (w / "status.md").write_text(f"# Status\nLast updated: {date.today():%Y-%m-%d} (commit abc1234)\n",
                                 encoding="utf-8")
    return w


def test_clean_wiki_passes(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    assert wl.check_static(w, today=date.today()) == []


def test_missing_component_page(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "gate.md").unlink()
    assert "missing-component: gate" in wl.check_static(w, today=date.today())


def test_missing_adr(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "adr" / "0007-x.md").unlink()
    assert "missing-adr: 0007" in wl.check_static(w, today=date.today())


@pytest.mark.parametrize("word", ["TODO", "TBD"])
def test_forbidden_words(tmp_path: Path, word: str) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "api.md").write_text(f"# C\n{word} later\n", encoding="utf-8")
    assert f"forbidden-word: components/api.md: {word}" in wl.check_static(w, today=date.today())


def test_broken_relative_link(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "api.md").write_text("[x](../nope.md)\n", encoding="utf-8")
    assert "broken-link: components/api.md -> ../nope.md" in wl.check_static(w, today=date.today())


def test_index_must_list_every_file(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "extra.md").write_text("# E\n", encoding="utf-8")
    assert "index-missing: components/extra.md" in wl.check_static(w, today=date.today())


def test_changed_files_rule_requires_wiki_change() -> None:
    assert wl.check_changed(["services/api/x.py"], pr_body="") == ["wiki-not-updated: services/api/x.py"]
    assert wl.check_changed(["services/api/x.py", "wiki/log.md"], pr_body="") == []
    assert wl.check_changed(["services/api/x.py"], pr_body="wiki-skip: typo only\n") == []
    assert wl.check_changed(["README.md"], pr_body="") == []


def test_status_staleness() -> None:
    assert wl.status_is_stale(status_date=date(2026, 12, 1), latest_code_commit=date(2026, 12, 9))
    assert not wl.status_is_stale(status_date=date(2026, 12, 3), latest_code_commit=date(2026, 12, 9))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/repo/test_wiki_lint.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement `scripts/wiki_lint.py`**

```python
"""Wiki lint (WIK-020, WIK-021). Usage:
  uv run python scripts/wiki_lint.py                          # static checks
  uv run python scripts/wiki_lint.py --changed-files f.txt --pr-body body.txt
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPONENT_PAGES = [
    "console", "api", "agent", "gate", "faultlab", "mcp-telemetry", "mcp-k8s", "mcp-gitops",
    "migrate", "demo-seed", "postgres", "keycloak", "keycloak-config", "otel-collector",
    "kube-prometheus-stack", "loki", "tempo", "argocd", "chaos-mesh", "kyverno",
    "external-secrets", "cert-manager", "traefik", "workload", "telemetry", "capacity",
]
CODE_PREFIXES = ("services/", "libs/", "deploy/", "infra/", "policies/", "eval/")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
FORBIDDEN = ("TODO", "TBD")
STATUS_RE = re.compile(r"^Last updated: (\d{4}-\d{2}-\d{2})", re.M)


def check_static(wiki: Path, today: date) -> list[str]:
    problems: list[str] = []
    for slug in COMPONENT_PAGES:
        if not (wiki / "components" / f"{slug}.md").is_file():
            problems.append(f"missing-component: {slug}")
    for n in range(1, 26):
        if not list((wiki / "adr").glob(f"{n:04d}-*.md")):
            problems.append(f"missing-adr: {n:04d}")
    index_text = (wiki / "index.md").read_text(encoding="utf-8") if (wiki / "index.md").exists() else ""
    for page in sorted(wiki.rglob("*.md")):
        rel = page.relative_to(wiki).as_posix()
        text = page.read_text(encoding="utf-8")
        for word in FORBIDDEN:
            if re.search(rf"\b{word}\b", text):
                problems.append(f"forbidden-word: {rel}: {word}")
        for target in LINK_RE.findall(text):
            if re.match(r"^[a-z]+:", target):
                continue  # absolute URL
            if not (page.parent / target).resolve().exists():
                problems.append(f"broken-link: {rel} -> {target}")
        if rel != "index.md" and f"({rel})" not in index_text:
            problems.append(f"index-missing: {rel}")
    return problems


def status_is_stale(status_date: date, latest_code_commit: date) -> bool:
    return (latest_code_commit - status_date).days > 7


def check_status(wiki: Path) -> list[str]:
    m = STATUS_RE.search((wiki / "status.md").read_text(encoding="utf-8"))
    if not m:
        return ["status-format: missing 'Last updated: YYYY-MM-DD'"]
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", *CODE_PREFIXES], cwd=REPO,
        capture_output=True, text=True, check=False).stdout.strip()
    if not out:
        return []
    if status_is_stale(datetime.strptime(m.group(1), "%Y-%m-%d").date(),
                       datetime.strptime(out, "%Y-%m-%d").date()):
        return [f"status-stale: status.md {m.group(1)} vs last code commit {out}"]
    return []


def check_changed(changed: list[str], pr_body: str) -> list[str]:
    if re.search(r"^wiki-skip: \S.*$", pr_body, re.M):
        return []
    code = [f for f in changed if f.startswith(CODE_PREFIXES)]
    if code and not any(f.startswith("wiki/") for f in changed):
        return [f"wiki-not-updated: {f}" for f in code]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed-files")
    ap.add_argument("--pr-body")
    args = ap.parse_args()
    wiki = REPO / "wiki"
    problems = check_static(wiki, today=date.today()) + check_status(wiki)
    if args.changed_files:
        changed = Path(args.changed_files).read_text(encoding="utf-8").split()
        body = Path(args.pr_body).read_text(encoding="utf-8") if args.pr_body else ""
        problems += check_changed(changed, body)
    for p in problems:
        print(f"wiki-lint: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify the unit tests pass**

Run: `uv run pytest tests/repo/test_wiki_lint.py -v` → PASS.

- [ ] **Step 5: Create the wiki pages**

Content rules for every page: factual, dated, no `TODO`/`TBD`. Pages for things not built yet state `Status: not implemented yet — planned in <task ID>.` under the title.

| File | Required content |
|---|---|
| `wiki/index.md` | `# Rootline wiki`, a paragraph quoting WIK-001's spec/wiki split, then one bullet per wiki file: `- [<path>](<path>) — <one-line description>`. "Every wiki file" includes `adr/0037-swarm-state-dir.md`, `adr/0038-ruff-scope-and-formatting.md` and `adr/0039-commit-trailers.md`, which are on `develop` before this task starts (PG-18 … PG-20); without their bullets `wiki_lint.py` reports `index-missing` for them |
| `wiki/status.md` | WIK-012 format; `## Current milestone: Week 1 — Foundations`; In progress lists W1 tasks; Blockers `None` |
| `wiki/log.md` | `# Log` then `## <today>` and `- [agent] Created wiki skeleton (W1-T03)` |
| `wiki/architecture.md` | the spec §5.1 diagram verbatim in a code block; a table `| Component | Namespace | Spec | Wiki page |` for ARC-001 |
| `wiki/glossary.md` | the spec §2 table verbatim plus a `## Additions` section (empty table header) |
| `wiki/cost-ledger.md` | `# Cost ledger`; the CST-001 caps table; a weekly table `| Week of (Monday) | Anthropic dev | Anthropic cluster | Anthropic CI | Ledger dev/eval/ci | GCP to date | Total | Variance vs plan | Notes |` with the first row for week 1 at 0.00 |
| `wiki/adr/0000-template.md` | WIK-011 template: `# NNNN — <title>`, `Status: proposed`, `Date:`, `## Context`, `## Decision`, `## Consequences`, `## Alternatives considered`, `## Spec references` |
| `wiki/components/<slug>.md` | WIK-010 nine headings in order (Purpose, Requirement IDs, Interfaces, Configuration, Dependencies, Data owned, Failure modes and handling, Runbook links, Last verified) |
| `wiki/runbooks/workstation-setup.md` | sections in order: `## Windows side` (WSL 2 with distribution `Ubuntu` 26.04 LTS, the exact GEN-040 `.wslconfig` content, `wsl --shutdown`, the browser); `## WSL basics` (`/etc/wsl.conf` with `[boot] systemd=true` and `[user] default=arkhash0309`, `sudo apt update && sudo apt upgrade -y`, the support packages of GEN-040); `## Tools` — one subsection per GEN-040 row with the exact commands used on 2026-11-26 (root part: the script `~/rootline-root-setup.sh` — apt packages including `docker-buildx`, `[interop] appendWindowsPath=false`, Ollama installer with the service disabled; user part: release binaries into `~/.local/bin`, uv + Python 3.12, fnm + Node 24, the gcloud tarball with `gke-gcloud-auth-plugin`, the Linux Claude Code build; `gh` logged in as `arkhash0309` with `gh auth setup-git`; added in week 6: `npx playwright install --with-deps chromium`); `## Repositories` (clone into `/home/arkhash0309/projects/rootline` and `/home/arkhash0309/projects/rootline-env`, never under `/mnt/c`; VS Code users open them with the Remote - WSL extension); a section `## Anthropic` describing O-8 and PG-13; a section `## Verify` saying run `task doctor` |
| `wiki/versions.md` | title `# Versions` + `Status: not implemented yet — planned in W1-T02 step 8.` |
| `wiki/runbooks/local-up.md` | already created by W1-T08 (stage W1-S2): do not create or edit it; list it in `index.md` |
| `wiki/runbooks/capture-batch.md`, `gcp-bootstrap.md`, `gke-spin-up.md`, `gke-teardown.md`, `github-apps.md`, `interview-demo.md`, `recovery.md` | title + `Status: not implemented yet — planned in <task>` (capture-batch: W2-T12; gcp-bootstrap: W7-T01; gke-spin-up/teardown: W7-T06; github-apps: W2-T07 and W3-T10; interview-demo: W8-T06; recovery: W2-T12) |
| `wiki/security/threat-model.md` | the SEC-140 table verbatim; `Status: summary only — full STRIDE in W8-T04` |
| `wiki/eval/dataset.md`, `local-pilot.md`, `results.md` | title + status line (W2-T13, W4-T14, W4-T15) |

- [ ] **Step 6: Run the lint for real**

Run: `uv run python scripts/wiki_lint.py`
Expected: only `missing-adr: 0001` … `missing-adr: 0025` (fixed by W1-T04). Do not merge this PR until W1-T04 is merged into the same branch, or merge W1-T04 first. **Ordering rule:** create W1-T04 on top of this branch (`feat/w1-wiki`) and open a single PR for W1-T03 + W1-T04.

- [ ] **Step 7: Commit**

```bash
git add wiki scripts/wiki_lint.py tests/repo/test_wiki_lint.py
git commit -m "docs(wiki): add wiki skeleton and wiki lint

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task W1-T04: Architecture decision records 0001–0036

**Requirement IDs:** WIK-011, spec §3, overview §5 (PG-1 … PG-17), S9.
**Depends on:** W1-T03 (same branch `feat/w1-wiki`).

**Files:**
- Create: `wiki/adr/0001-target-role.md` … `wiki/adr/0036-wsl-development.md` (36 files)
- Modify: `wiki/index.md` (list them), `docs/superpowers/specs/2026-11-25-rootline-design.md` §26 (rows already added at planning time; fill the `ADR` column links)
- Do not create, edit or renumber: `wiki/adr/0037-swarm-state-dir.md`, `wiki/adr/0038-ruff-scope-and-formatting.md`, `wiki/adr/0039-commit-trailers.md`. The planner wrote them on 2026-11-26 (branch `docs/w1-plan-gaps`, PG-18 … PG-20), so they are on `develop` before stage W1-P1 starts. Their spec §26 rows already link them; leave those three rows unchanged. The next free ADR number after this task is **0040**.

- [ ] **Step 1: Write each ADR from this table**

Every file uses the WIK-011 template. `Status: accepted`, `Date: <today>`. **Context** = the "Primary reason" (spec §3) or the PG problem statement, expanded to 2–4 sentences. **Decision** = the Choice column verbatim plus the spec requirement IDs that implement it. **Consequences** and **Alternatives considered** as below. **Spec references** = the IDs listed.

| ADR | File slug | Alternatives considered | Consequences | Spec refs |
|---|---|---|---|---|
| 0001 | `target-role` | ML research engineer; data scientist | Every feature must show LLM engineering depth | §1.3, G1 |
| 0002 | `product-concept` | RAG over docs; coding agent | Needs a live cluster and fault lab | §1.2 |
| 0003 | `workload` | Online Boutique; custom microservices | Chart pinned to 0.42.8; trimming per WKL-002/003 | WKL-001–011 |
| 0004 | `models` | Opus 5.5 large ($4/$20); single model | Routed config is the default; owner may add Opus later | AGT-050, AGT-051, C3 |
| 0005 | `llm-access-layer` | LiteLLM proxy; LangChain chat models | We own retries, budgets, batches | AGT-060–066, C1 |
| 0006 | `cloud` | AWS EKS; Azure AKS | Zonal free tier; spot nodes can be preempted | INF-010, C10 |
| 0007 | `hosting-model` | Always-on cluster | Demo needs `task gke:up` (≤ 25 min) | INF-001, S1 |
| 0008 | `autonomy` | Human approval for all; full autonomy | Threshold calibrated by EVL-061 | POL-030–032 |
| 0009 | `user-idp` | Auth0/Okta free tier; Dex | Passkeys must be re-registered per GKE spin-up | SEC-010–023a |
| 0010 | `agent-delegation` | Impersonation; static API keys | Preview risk → `azp` fallback; final mode decided in W3-T03 (this ADR is updated then) | SEC-040–044 |
| 0011 | `agent-workload-identity` | Client secrets in Secrets | Needs projected SA tokens and issuer discovery | SEC-032, SEC-033 |
| 0012 | `mcp-revision` | Revision 2025-11-25 | Record the SDK fallback if W1-T02 hit it; SEC-052 deviation | MCP-001, SEC-051, SEC-052 |
| 0013 | `agent-tracing` | LangSmith; self-hosted Langfuse | Unit budgeting and sampling | OBS-020–023 |
| 0014 | `job-queue` | Redis/RQ; Kafka | Lease + reaper code in the agent | AGT-030 |
| 0015 | `database` | Cloud SQL; SQLite | Backups disabled; seed dump | DB-001 |
| 0016 | `gitops-repositories` | Single repo | Two deploy keys; env repo bot-only | GEN-010–012, C4 |
| 0017 | `manifest-tooling` | Kustomize | Workload rendered once; exact diffs | WKL-010, C5 |
| 0018 | `image-registry` | GHCR | WIF for CI; cleanup policy | INF-004, CI-001 |
| 0019 | `task-runner` | Make; npm scripts | Python helpers for anything non-trivial; same commands in WSL and CI | GEN-041, GEN-060 |
| 0020 | `embeddings` | Voyage; OpenAI embeddings | 384-dim vectors | AGT-090 |
| 0021 | `ingress` | ingress-nginx; Gateway with Envoy | Same HTTPRoutes locally and on GKE | INF-030, INF-040 |
| 0022 | `wiki` | External Notion/Confluence | Wiki lint in CI | WIK-* |
| 0023 | `fix-catalogue` | Free-form patches; `toggle_flag` | Flags fixed by `resync_app` | POL-020 |
| 0024 | `evaluation-execution` | In-cluster eval jobs | Ollama runs in WSL with the cluster stopped | EVL-062, C13 |
| 0025 | `branching` | Trunk-based | Release PR per week | GEN-020 |
| 0026 | `structured-outputs-raw-schema` | `messages.parse` interactive + raw schema in batch | Own schema transform; Pydantic re-validation | PG-1, AGT-052, AGT-062 |
| 0027 | `no-fallbacks-in-batch` | Client-side fallback middleware | Batch refusals retried once then fail | PG-2 |
| 0028 | `planning-schedule-adjustments` | Follow §22 literally | faultlab App in W2; argocd-accounts, redaction, algorithms, detector in W2; LAB-046 in W3; eval-smoke gated until W7 | PG-3, PG-4, PG-7 |
| 0029 | `snapshot-parity-flag` | Delay capture to week 3 | Week-2 snapshots unverified by parity | PG-5, MCP-053 |
| 0030 | `acceptable-action-constraints` | Encode constraints as strings in ActionSpec | New `AcceptableAction` model | PG-6, LAB-050, POL-021 |
| 0031 | `root-tests-directory` | Put e2e under `scripts/` | Root `tests/` limited to repo, fixtures, e2e | PG-8 |
| 0032 | `secret-bootstrap` | Sealed Secrets; ESO for repo creds | Repo creds and DB passwords handled per PG-9/PG-10; host key name per PG-13 | PG-9, PG-10, PG-13 |
| 0033 | `workload-render-refinements` | Keep init-copy and restart flagd always | Live flag drift possible; collector FQDN | PG-11, PG-12 |
| 0034 | `batch-ids-and-caching` | Truncate IDs; system-block-only caching | Hashed batch `custom_id` with a mapping file; extra top-level cache breakpoint | PG-14, PG-15 |
| 0035 | `swarm-execution` | One agent implementing tasks in sequence; per-task PRs straight into develop | Parallel stages in worktrees, integration branches, integration gate; fixed role models (Haiku 5.5 coordinator, Opus 5.5 planner and reviewer, Sonnet 5.5 implementer, high effort except the coordinator) | PG-16, overview §7, CLAUDE.md |
| 0036 | `wsl-development` | Windows-native PowerShell/Git Bash with Docker Desktop | All development in WSL 2 Ubuntu 26.04 with native Docker Engine; repos on the WSL filesystem; Windows keeps the browser; CA trusted in WSL and Windows | PG-17, GEN-040, GEN-041 |

- [ ] **Step 2: Update `wiki/index.md`, then run the lint**

Run: `uv run python scripts/wiki_lint.py` → exit 0.
Run: `uv run pytest tests/repo -v` → PASS.

- [ ] **Step 3: Commit, push, open the combined PR for W1-T03 + W1-T04**

```bash
git add wiki docs/superpowers/specs/2026-11-25-rootline-design.md
git commit -m "docs(wiki): add ADRs 0001-0036

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -u origin feat/w1-wiki
gh pr create --base develop --title "docs(wiki): wiki skeleton, lint and ADRs" --body-file .github/pull_request_template.md
```

Fill the PR body sections before creating (Requirement IDs: WIK-001–021, §3; Tests: the two commands above).

---

### Task W1-T05: `rootline-wiki` agent skill

**Requirement IDs:** WIK-030.
**Depends on:** W1-T04 merged. **Branch:** `feat/w1-wiki-skill`.

**Files:**
- Create: `.claude/skills/rootline-wiki/SKILL.md`
- Test: `tests/repo/test_skill.py`

- [ ] **Step 1 (pre-dispatch, coordinator — overview §7.3): Load the superpowers `writing-skills` skill** and follow its process; the coordinator dispatches a fresh `rootline-implementer` (Sonnet 5.5, high) as the test subject and passes the recorded baseline to the W1-T05 implementer (it requires a baseline test of agent behaviour without the skill; use the scenario "implement a one-line change in `libs/py-common` and finish the task" and record whether the agent updated `wiki/log.md` and ran `task wiki:lint`).

- [ ] **Step 2: Write the failing test**

```python
"""Verifies WIK-030."""
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[2] / ".claude/skills/rootline-wiki/SKILL.md"


def test_skill_front_matter_and_sections() -> None:
    text = SKILL.read_text(encoding="utf-8")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm)
    assert meta["name"] == "rootline-wiki"
    for word in ("implementation", "planning", "debugging", "review"):
        assert word in meta["description"]
    for heading in ("## Before work", "## During work", "## After work", "## Rules", "## Templates"):
        assert heading in body
    for needle in ("wiki/index.md", "wiki/status.md", "§0.3", "task wiki:lint", "unverified",
                   "Never copy secrets", "WIK-020"):
        assert needle in body
```

Run: `uv run pytest tests/repo/test_skill.py -v` → FAIL.

- [ ] **Step 3: Write `SKILL.md`**

```markdown
---
name: rootline-wiki
description: Use for any Rootline implementation, planning, debugging or review task in this repository - loads current project state from wiki/ before work and records what changed after work.
---

# Rootline wiki

The wiki in `wiki/` is the working memory for agents building Rootline. The spec
(`docs/superpowers/specs/2026-11-25-rootline-design.md`) says what must be true; the wiki says what is
true now and why.

## Before work

1. Read `wiki/index.md` and `wiki/status.md`.
2. Read the `wiki/components/*.md` pages for every component you will touch.
3. Read the spec sections for the requirement IDs in your task (search the spec for each ID).
4. Read the plan task you are executing in `docs/superpowers/plans/`.

## During work

- If the spec does not answer a question you need answered, follow spec §0.3: choose the simplest,
  cheapest, safest option, write an ADR in `wiki/adr/` (next free number, label `spec-gap`), and add a
  row to spec §26 in the same pull request. If the choice changes cost, security, scope or something the
  owner approved, stop and ask the owner first.
- Write facts into the wiki only after you verified them in this repository or cluster.

## After work

Perform all WIK-020 obligations in the same pull request:
1. Update the affected component or runbook pages (sections per the component template below).
2. Append an entry to `wiki/log.md`.
3. Update `wiki/status.md` if a plan task changed state.
4. Add an ADR for any new decision or deviation from the spec.
Then run `task wiki:lint` and fix every reported problem.

## Rules

- The wiki records facts verified in this repository. Mark anything not verified as
  "unverified (YYYY-MM-DD)".
- Never copy secrets, tokens, keys or passwords into the wiki.
- Keep pages factual and dated. Every component page ends with "Last verified: <date>, <commit sha7>".
- Prefer editing an existing page to creating a new one. A new page must be added to `wiki/index.md`.
- Follow the documentation rule in `CLAUDE.md`.

## Templates

### Component page (WIK-010)
    # <component>
    ## Purpose
    ## Requirement IDs
    ## Interfaces
    ## Configuration
    | Env var | Default | Meaning |
    ## Dependencies
    ## Data owned
    ## Failure modes and handling
    ## Runbook links
    ## Last verified
    <YYYY-MM-DD>, <commit sha7>

### ADR (WIK-011)
    # NNNN — <title>
    Status: proposed | accepted | superseded by NNNN
    Date: YYYY-MM-DD
    ## Context
    ## Decision
    ## Consequences
    ## Alternatives considered
    ## Spec references

### status.md (WIK-012)
    # Status
    Last updated: YYYY-MM-DD (commit <sha7>)
    ## Current milestone: Week N — <name>
    ## Done
    - <item> (PR #n, REQ IDs)
    ## In progress
    - <item> — <owner: agent|owner> — <next step>
    ## Next
    - <item>
    ## Blockers
    - <blocker> (or "None")

### log.md entry (WIK-013)
    ## YYYY-MM-DD
    - [agent|owner] <what happened> (PR #n / commit sha7)
```

- [ ] **Step 4 (deferred to W1-S3, coordinator): Verify with the writing-skills process** (re-run the baseline scenario with the skill loaded; the agent must update `wiki/log.md` and run `task wiki:lint`). Record the result in `wiki/log.md`.

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest tests/repo/test_skill.py -v` → PASS.

```bash
git add .claude/skills/rootline-wiki/SKILL.md tests/repo/test_skill.py wiki/log.md
git commit -m "docs: add rootline-wiki agent skill

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task W1-T06: Taskfile, `task doctor` and `.env.example`

**Requirement IDs:** GEN-040, GEN-041, GEN-060, SEC-101, S2, PG-13.
**Depends on:** W1-T02. **Branch:** `feat/w1-taskfile`.

**Files:**
- Create: `Taskfile.yml`, `scripts/doctor.py`, `.env.example` (`scripts/proc.py` already exists, created by W1-T16)
- Test: `tests/repo/test_doctor.py`

**Interfaces:**
- Consumes: `scripts.proc.run(cmd: list[str], *, check: bool = True, capture: bool = True, env: dict | None = None, timeout: int = 600, input_text: str | None = None) -> subprocess.CompletedProcess[str]` (created by W1-T16 with the code in step 2).
- Produces: `scripts.doctor.Check(name: str, status: Literal["OK","WARN","FAIL"], detail: str)`; `scripts.doctor.memory_requests_gib(pods_json: dict) -> float`; `scripts.doctor.env_key_checks(example: str, local: dict[str,str], week: int) -> list[Check]`.

**`.env.example` format.** One key per line, `KEY=` with an empty value, each preceded by a comment `# week: N — <purpose>` giving the week from which the key is required:

```dotenv
# week: 1 — read-only deploy key for arkhash0309/rootline (PEM, quoted multi-line)
DEPLOY_KEY_ROOTLINE=
# week: 1 — read-only deploy key for arkhash0309/rootline-env (PEM, quoted multi-line)
DEPLOY_KEY_ROOTLINE_ENV=
# week: 1 — local checkout path of rootline-env inside WSL (absolute Linux path: /home/arkhash0309/projects/rootline-env)
ROOTLINE_ENV_DIR=
# week: 2 — GitHub App rootline-faultlab
GH_APP_FAULTLAB_ID=
GH_APP_FAULTLAB_INSTALLATION_ID=
GH_APP_FAULTLAB_PRIVATE_KEY=
# week: 3 — GitHub App rootline-agent
GH_APP_AGENT_ID=
GH_APP_AGENT_INSTALLATION_ID=
GH_APP_AGENT_PRIVATE_KEY=
# week: 3 — GitHub App rootline-gate
GH_APP_GATE_ID=
GH_APP_GATE_INSTALLATION_ID=
GH_APP_GATE_PRIVATE_KEY=
# week: 3 — Keycloak seed user passwords (SEC-020)
SEED_OWNER=
SEED_INTERVIEWER=
SEED_VIEWER1=
SEED_BREAKGLASS=
# week: 3 — base32 TOTP seed for breakglass (SEC-022)
SEED_BREAKGLASS_OTP_SEED=
# week: 4 — in-cluster Anthropic key "rootline-cluster" (SEC-100, PG-13)
ANTHROPIC_API_KEY=
# week: 4 — host Anthropic key "rootline-dev" for eval runner and pilots (PG-13)
ROOTLINE_HOST_ANTHROPIC_API_KEY=
# week: 4 — Langfuse Cloud project rootline
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=
# week: 8 — Hugging Face username for publish-hf (EVL-100)
HF_USER=
```

`.env.gke` has the same keys (created by the owner in week 7).

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies GEN-060 (doctor), SEC-101, S2."""
from scripts import doctor

EXAMPLE = """# week: 1 — a
A=
# week: 4 — b
B=
"""


def test_env_keys_required_by_week() -> None:
    checks = doctor.env_key_checks(EXAMPLE, {"A": "x"}, week=1)
    assert [(c.name, c.status) for c in checks] == [("env:A", "OK"), ("env:B", "WARN")]
    checks = doctor.env_key_checks(EXAMPLE, {"A": "x"}, week=4)
    assert ("env:B", "FAIL") in [(c.name, c.status) for c in checks]


def test_empty_value_counts_as_missing() -> None:
    checks = doctor.env_key_checks(EXAMPLE, {"A": ""}, week=1)
    assert checks[0].status == "FAIL"


def test_memory_requests_sum() -> None:
    pods = {"items": [
        {"status": {"phase": "Running"}, "spec": {"containers": [
            {"resources": {"requests": {"memory": "512Mi"}}},
            {"resources": {"requests": {"memory": "1Gi"}}}],
            "initContainers": [{"resources": {"requests": {"memory": "4Gi"}}}]}},
        {"status": {"phase": "Succeeded"}, "spec": {"containers": [
            {"resources": {"requests": {"memory": "8Gi"}}}]}},
    ]}
    assert doctor.memory_requests_gib(pods) == 1.5  # init containers and finished pods excluded


def test_parse_week_from_status() -> None:
    assert doctor.current_week("## Current milestone: Week 3 — Identity and MCP\n") == 3


def test_check_line_format() -> None:
    assert doctor.Check("git", "OK", "2.47.1").line() == "OK   git: 2.47.1"


def test_wsl_checks() -> None:
    """Verifies GEN-040, GEN-041 (PG-17)."""
    from pathlib import Path
    ok = doctor.wsl_checks("Linux version 6.6.114.1-microsoft-standard-WSL2", Path("/home/arkhash0309/projects/rootline"),
                           {"WSL_DISTRO_NAME": "Ubuntu"})
    assert [(c.name, c.status) for c in ok][:2] == [("wsl", "OK"), ("repo-location", "OK")]
    bad = doctor.wsl_checks("Linux version 6.8.0-generic", Path("/mnt/c/Users/arkha/rootline"), {})
    assert [(c.name, c.status) for c in bad][:2] == [("wsl", "FAIL"), ("repo-location", "FAIL")]
```

Run: `uv run pytest tests/repo/test_doctor.py -v` → FAIL.

- [ ] **Step 2: Reference code of `scripts/proc.py`** (W1-T16 creates the file with exactly this code; confirm it matches and do not recreate it)

```python
"""Subprocess helper used by every Taskfile script (GEN-041)."""
from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping


def run(cmd: list[str], *, check: bool = True, capture: bool = True,
        env: Mapping[str, str] | None = None, timeout: int = 600,
        input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, env=full_env,
                          timeout=timeout, input=input_text)
```

- [ ] **Step 3: Implement `scripts/doctor.py`**

```python
"""task doctor (GEN-060): prerequisites, Docker memory, .env.local keys, cluster memory requests."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
MEMORY_CAP_GIB = 9.5
UNITS = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "K": 10**3, "M": 10**6, "G": 10**9}


@dataclass(frozen=True)
class Check:
    name: str
    status: Literal["OK", "WARN", "FAIL"]
    detail: str

    def line(self) -> str:
        return f"{self.status:<4} {self.name}: {self.detail}"


def parse_bytes(q: str) -> int:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGT]i?)?", q)
    if not m:
        raise ValueError(q)
    return int(float(m.group(1)) * UNITS.get(m.group(2) or "", 1))


def memory_requests_gib(pods: dict) -> float:
    total = 0
    for pod in pods["items"]:
        if pod["status"].get("phase") in ("Succeeded", "Failed"):
            continue
        for c in pod["spec"].get("containers", []):
            req = c.get("resources", {}).get("requests", {}).get("memory")
            if req:
                total += parse_bytes(req)
    return round(total / 2**30, 3)


def current_week(status_text: str) -> int:
    m = re.search(r"Current milestone: Week (\d+)", status_text)
    return int(m.group(1)) if m else 1


def env_key_checks(example: str, local: dict[str, str | None], week: int) -> list[Check]:
    checks, key_week = [], 1
    for line in example.splitlines():
        if m := re.match(r"# week: (\d+)", line):
            key_week = int(m.group(1))
        elif m := re.match(r"([A-Z0-9_]+)=", line):
            key = m.group(1)
            present = bool(local.get(key))
            if present:
                checks.append(Check(f"env:{key}", "OK", "set"))
            else:
                status = "FAIL" if key_week <= week else "WARN"
                checks.append(Check(f"env:{key}", status, f"missing (required from week {key_week})"))
    return checks


TOOLS = {  # name -> (version command, regex extracting the version)
    "docker": (["docker", "version", "--format", "{{.Server.Version}}"], r"(\S+)"),
    "k3d": (["k3d", "version"], r"k3d version v(\S+)"),
    "kubectl": (["kubectl", "version", "--client", "-o", "json"], r'"gitVersion":\s*"v(\S+?)"'),
    "helm": (["helm", "version", "--short"], r"v(\S+?)\+"),
    "task": (["task", "--version"], r"(\d+\.\d+\.\d+)"),
    "uv": (["uv", "--version"], r"uv (\S+)"),
    "node": (["node", "--version"], r"v(\S+)"),
    "terraform": (["terraform", "version", "-json"], r'"terraform_version":\s*"(\S+?)"'),
    "gcloud": (["gcloud", "version", "--format=json"], r'"Google Cloud SDK":\s*"(\S+?)"'),
    "gh": (["gh", "--version"], r"gh version (\S+)"),
    "ollama": (["ollama", "--version"], r"(\d+\.\d+\.\d+)"),
    "opa": (["opa", "version"], r"Version: (\S+)"),
    "git": (["git", "--version"], r"git version (\d+\.\d+\.\d+)"),
}


def tool_checks() -> list[Check]:
    out = []
    for name, (cmd, rx) in TOOLS.items():
        if shutil.which(cmd[0]) is None:
            out.append(Check(name, "FAIL", "not on PATH"))
            continue
        r = run(cmd, check=False)
        m = re.search(rx, r.stdout + r.stderr)
        out.append(Check(name, "OK" if m else "WARN", m.group(1) if m else "version not parsed"))
    git = next(c for c in out if c.name == "git")
    if git.status == "OK" and tuple(int(x) for x in git.detail.split(".")[:2]) < (2, 45):
        out[out.index(git)] = Check("git", "FAIL", f"{git.detail} < 2.45")
    gh = run(["gh", "api", "user", "--jq", ".login"], check=False)
    out.append(Check("gh-account", "OK" if gh.stdout.strip() == "arkhash0309" else "FAIL",
                     gh.stdout.strip() or "not authenticated"))
    return out


def docker_memory_check() -> Check:
    r = run(["docker", "info", "--format", "{{.MemTotal}}"], check=False)
    try:
        gib = int(r.stdout.strip()) / 2**30
    except ValueError:
        return Check("docker-memory", "FAIL", "docker not running")
    return Check("docker-memory", "OK" if gib >= 11.5 else "FAIL",
                 f"{gib:.1f} GiB (need ≥ 11.5; native Docker Engine sees the WSL VM memory set by .wslconfig)")


def cluster_memory_check() -> Check:
    r = run(["kubectl", "--context", "k3d-rootline", "get", "pods", "-A", "-o", "json"], check=False)
    if r.returncode != 0:
        return Check("memory_requests_total", "WARN", "cluster k3d-rootline not reachable")
    gib = memory_requests_gib(json.loads(r.stdout))
    print(f"memory_requests_total={gib} GiB")
    return Check("memory_requests_total", "OK" if gib <= MEMORY_CAP_GIB else "FAIL",
                 f"{gib} GiB (cap {MEMORY_CAP_GIB})")


def wsl_checks(proc_version: str, repo: Path, env: dict[str, str]) -> list[Check]:
    """GEN-040/041 (PG-17): run inside WSL 2, repo on the WSL filesystem, systemd Docker."""
    out = [Check("wsl", "OK" if "microsoft" in proc_version.lower() and env.get("WSL_DISTRO_NAME") else "FAIL",
                 env.get("WSL_DISTRO_NAME", "not running inside WSL"))]
    on_windows_fs = str(repo).startswith("/mnt/")
    out.append(Check("repo-location", "FAIL" if on_windows_fs else "OK",
                     f"{repo} ({'Windows filesystem: move to /home/arkhash0309/projects' if on_windows_fs else 'WSL filesystem'})"))
    cpus = os.cpu_count() or 0
    out.append(Check("wsl-cpus", "OK" if cpus >= 16 else "WARN", f"{cpus} (.wslconfig processors=16)"))
    return out


def main() -> int:
    week = current_week((REPO / "wiki/status.md").read_text(encoding="utf-8"))
    local = dotenv_values(REPO / ".env.local") if (REPO / ".env.local").exists() else {}
    checks = wsl_checks(Path("/proc/version").read_text(encoding="utf-8"), REPO, dict(os.environ)) + tool_checks() + \
        [docker_memory_check()]
    checks += env_key_checks((REPO / ".env.example").read_text(encoding="utf-8"), dict(local), week)
    checks.append(cluster_memory_check())
    for c in checks:
        print(c.line())
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
```

Add `python-dotenv` to the root `dev` dependency group (`uv add --dev python-dotenv`).

- [ ] **Step 4: Write `Taskfile.yml`**

```yaml
version: "3"

dotenv: [".env.local"]

env:
  SSL_CERT_FILE: /etc/ssl/certs/ca-certificates.crt        # Python/httpx in WSL trust the local CA after task trust-ca (PG-17)
  NODE_EXTRA_CA_CERTS: /usr/local/share/ca-certificates/rootline-ca.crt

vars:
  PY: uv run python
  REVISION: '{{.REVISION | default "develop"}}'

tasks:
  doctor:
    desc: Check prerequisites, Docker memory, .env.local keys and cluster memory requests (GEN-060)
    cmds: ["{{.PY}} scripts/doctor.py"]

  up:
    desc: Create k3d cluster rootline and deploy everything via ArgoCD (GEN-060, INF-030)
    cmds: ["{{.PY}} scripts/up.py --revision {{.REVISION}}"]

  down:
    desc: Delete k3d cluster rootline (keeps .env.local and data/)
    cmds: ["k3d cluster delete rootline"]

  stop:
    desc: Stop the k3d cluster (frees RAM for Ollama)
    cmds: ["k3d cluster stop rootline"]

  start:
    desc: Start the k3d cluster
    cmds: ["k3d cluster start rootline"]

  images:
    desc: Build all service images with tag dev and import them into k3d
    cmds: ["{{.PY}} scripts/build_images.py --tag dev --import-k3d rootline"]

  secrets:local:
    desc: Create rootline-secrets/rootline-bootstrap and ArgoCD repo secrets from .env.local (SEC-100, PG-9)
    cmds: ["{{.PY}} scripts/secrets_local.py"]

  trust-ca:
    desc: Trust the local CA in WSL (system store + NSS) and in the Windows user Root store (INF-031, GEN-060)
    cmds: ["{{.PY}} scripts/trust_ca.py {{.CLI_ARGS}}"]

  test:
    desc: All unit tests (Python, console, OPA)
    cmds:
      - uv run pytest -m "not integration and not k8s" --cov --cov-report=term-missing
      - "{{.PY}} scripts/run_if_exists.py apps/console/package.json -- npm --prefix apps/console run test"
      - "{{.PY}} scripts/run_if_exists.py policies/opa/rootline -- opa test policies/opa -v"

  test:integration:
    desc: Integration tests (Docker required)
    cmds: [uv run pytest -m integration -v]

  lint:
    desc: ruff, mypy, eslint, tsc, helm lint, kubeconform, terraform fmt, tflint
    cmds: ["{{.PY}} scripts/lint.py"]

  wiki:lint:
    desc: Wiki lint (WIK-021)
    cmds: ["{{.PY}} scripts/wiki_lint.py"]

  versions:render:
    desc: Regenerate files derived from versions.yaml
    cmds: ["{{.PY}} scripts/render_versions.py"]

  swarm:validate:
    desc: Validate the execution schedule (overview §7.2)
    cmds: ["{{.PY}} scripts/swarm_schedule.py validate"]

  swarm:next:
    desc: Print the next runnable stage of a week (task swarm:next -- --week N)
    cmds: ["{{.PY}} scripts/swarm_schedule.py next {{.CLI_ARGS}}"]

  integrate:gate:
    desc: Run integration gate checks G1-G11 (task integrate:gate -- --stage W2-P1 [--branch ref] [--pr-body file])
    cmds: ["{{.PY}} scripts/integration_gate.py {{.CLI_ARGS}}"]

  smoke:cluster:
    desc: Run cluster smoke check G12 against k3d-rootline
    cmds: ["{{.PY}} scripts/cluster_smoke.py {{.CLI_ARGS}}"]
```

`scripts/run_if_exists.py` (create now): `run_if_exists.py <path> -- <cmd...>` runs the command only if `<path>` exists, otherwise prints `skip: <path> missing` and exits 0. `scripts/lint.py` (create now) runs, in order and only when the relevant files exist: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy services libs eval/runner`, `npm --prefix apps/console run lint`, `npm --prefix apps/console run typecheck`, `helm lint` for every chart under `deploy/`, `scripts/render_manifests.py | kubeconform -strict -summary -ignore-missing-schemas` (created in W1-T10), `terraform fmt -check -recursive infra/terraform`, `tflint --recursive --chdir infra/terraform`; it exits non-zero if any step fails and prints one summary line per step. `scripts/up.py`, `scripts/build_images.py`, `scripts/secrets_local.py`, `scripts/trust_ca.py` are created in W1-T12 and W1-T10; until then the corresponding tasks fail with "No such file", which is expected.

- [ ] **Step 5: Run tests and the doctor**

Run: `uv run pytest tests/repo/test_doctor.py -v` → PASS.
Run: `task doctor` → prints one line per check. FAIL lines for missing tools are fixed by the owner using `wiki/runbooks/workstation-setup.md`; FAIL for `env:DEPLOY_KEY_*` is expected until O-2.

- [ ] **Step 6: Commit**

```bash
git add Taskfile.yml scripts .env.example tests/repo/test_doctor.py pyproject.toml uv.lock
git commit -m "build: add Taskfile, task doctor and .env.example

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task W1-T07: `rootline_common` foundation modules

**Requirement IDs:** ARC-020, API-002, API-004, API-006, OBS-001, GEN-002.
**Depends on:** W1-T02. **Parallel-safe** with W1-T03…T06. **Branch:** `feat/w1-py-common`.

**Files:**
- Create: `libs/py-common/rootline_common/{ids,timeutil,logging,problem,health,requestid,otel,settings}.py`
- Modify: `libs/py-common/pyproject.toml` dependencies: `fastapi`, `pydantic`, `pydantic-settings`, `python-ulid`, `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-httpx`, `opentelemetry-instrumentation-psycopg`, `httpx` (constraints per W1-T02)
- Test: `libs/py-common/tests/test_ids.py`, `test_timeutil.py`, `test_logging.py`, `test_problem.py`, `test_health.py`, `test_requestid.py`

**Interfaces:** Produces the W1-T07 rows of overview §3.1 exactly.

- [ ] **Step 1: Write the failing tests**

`libs/py-common/tests/test_ids.py`:

```python
"""Verifies GEN glossary 'ULID', OBS-020 (trace id mapping)."""
from rootline_common.ids import is_ulid, new_ulid, ulid_to_trace_id


def test_new_ulid_shape() -> None:
    u = new_ulid()
    assert len(u) == 26 and is_ulid(u)


def test_is_ulid_rejects() -> None:
    assert not is_ulid("not-a-ulid")
    assert not is_ulid("01ARZ3NDEKTSV4RRFFQ69G5FAI")  # I is not Crockford


def test_trace_id_is_128_bit_hex() -> None:
    from ulid import ULID
    u = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert ulid_to_trace_id(u) == ULID.from_str(u).bytes.hex()
    assert len(ulid_to_trace_id(new_ulid())) == 32
```

`libs/py-common/tests/test_timeutil.py`:

```python
"""Verifies API-006, MCP-002 timestamp format."""
from datetime import UTC, datetime, timedelta, timezone

from rootline_common.timeutil import parse_rfc3339, to_rfc3339, utcnow


def test_utcnow_is_aware_utc() -> None:
    assert utcnow().tzinfo is UTC


def test_to_rfc3339_ms_z() -> None:
    dt = datetime(2026, 11, 30, 9, 5, 7, 123456, tzinfo=UTC)
    assert to_rfc3339(dt) == "2026-11-30T09:05:07.123Z"
    assert to_rfc3339(dt, ms=False) == "2026-11-30T09:05:07Z"


def test_to_rfc3339_converts_other_zones() -> None:
    dt = datetime(2026, 11, 30, 14, 35, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert to_rfc3339(dt) == "2026-11-30T09:05:00.000Z"


def test_parse_roundtrip() -> None:
    assert parse_rfc3339("2026-11-30T09:05:07.123Z") == datetime(2026, 11, 30, 9, 5, 7, 123000, tzinfo=UTC)
```

`libs/py-common/tests/test_logging.py`:

```python
"""Verifies OBS-001 log format."""
import json
import logging

from rootline_common.logging import configure_logging, investigation_id_var, request_id_var


def test_json_log_line(capsys) -> None:
    configure_logging("api", "INFO")
    request_id_var.set("01ARZ3NDEKTSV4RRFFQ69G5FAV")
    investigation_id_var.set(None)
    logging.getLogger("rootline.test").info("hello %s", "world")
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["msg"] == "hello world"
    assert line["level"] == "INFO"
    assert line["logger"] == "rootline.test"
    assert line["component"] == "api"
    assert line["request_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert "investigation_id" not in line
    assert line["ts"].endswith("Z")
```

`libs/py-common/tests/test_problem.py`:

```python
"""Verifies API-002."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from rootline_common.problem import PROBLEM_CODES, Problem, install_problem_handlers


def make_app() -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)

    class Body(BaseModel):
        n: int

    @app.get("/boom")
    def boom() -> None:
        raise Problem("invalid_transition", 409, "Invalid transition", "queued -> merged")

    @app.post("/validate")
    def validate(body: Body) -> dict:
        return {}

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret detail")

    return app


def test_problem_shape() -> None:
    r = TestClient(make_app()).get("/boom", headers={"X-Request-Id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"})
    assert r.status_code == 409
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body == {"type": "https://rootline.dev/problems/invalid_transition", "title": "Invalid transition",
                    "status": 409, "detail": "queued -> merged", "instance": "/boom",
                    "code": "invalid_transition", "request_id": body["request_id"]}


def test_validation_error_has_errors_list() -> None:
    r = TestClient(make_app()).post("/validate", json={"n": "x"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    assert r.json()["errors"][0]["loc"] == ["body", "n"]


def test_internal_error_hides_detail() -> None:
    r = TestClient(make_app(), raise_server_exceptions=False).get("/crash")
    assert r.status_code == 500 and r.json()["code"] == "internal"
    assert "secret detail" not in r.text


def test_codes_table() -> None:
    assert PROBLEM_CODES == {
        "unauthenticated": 401, "insufficient_user_authentication": 401, "forbidden": 403,
        "not_found": 404, "validation_error": 422, "invalid_transition": 409, "conflict": 409,
        "separation_of_duties": 403, "rate_limited": 429, "lab_busy": 409, "internal": 500}
```

`libs/py-common/tests/test_health.py`:

```python
"""Verifies ARC-020."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rootline_common.health import make_health_router


async def ok() -> bool:
    return True


async def down() -> bool:
    return False


def test_ready_and_live() -> None:
    app = FastAPI()
    app.include_router(make_health_router({"db": ok, "keycloak": down}))
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200
    r = c.get("/readyz")
    assert r.status_code == 503 and r.json() == {"failing": ["keycloak"]}
    assert c.get("/metrics").status_code == 200


def test_check_exception_counts_as_failing() -> None:
    async def boom() -> bool:
        raise ConnectionError

    app = FastAPI()
    app.include_router(make_health_router({"db": boom}))
    assert TestClient(app).get("/readyz").json() == {"failing": ["db"]}
```

`libs/py-common/tests/test_requestid.py`:

```python
"""Verifies API-004."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rootline_common.ids import is_ulid
from rootline_common.logging import request_id_var
from rootline_common.requestid import RequestIdMiddleware


def make() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/x")
    def x() -> dict:
        return {"rid": request_id_var.get()}

    return TestClient(app)


def test_valid_incoming_id_is_kept() -> None:
    r = make().get("/x", headers={"X-Request-Id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"})
    assert r.headers["X-Request-Id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV" == r.json()["rid"]


def test_invalid_incoming_id_is_replaced() -> None:
    r = make().get("/x", headers={"X-Request-Id": "abc"})
    assert r.headers["X-Request-Id"] != "abc" and is_ulid(r.headers["X-Request-Id"])
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest libs/py-common/tests -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement the modules**

`ids.py`:

```python
"""ULID helpers (spec §2 'ULID', OBS-020)."""
import re

from ulid import ULID

_CROCKFORD = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def new_ulid() -> str:
    return str(ULID())


def is_ulid(value: str) -> bool:
    return bool(_CROCKFORD.fullmatch(value or ""))


def ulid_to_trace_id(ulid: str) -> str:
    return ULID.from_str(ulid).bytes.hex()
```

`timeutil.py`:

```python
"""Time helpers: RFC 3339 UTC with Z (API-006, MCP-002)."""
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_rfc3339(dt: datetime, *, ms: bool = True) -> str:
    dt = dt.astimezone(UTC)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{dt.microsecond // 1000:03d}Z" if ms else f"{base}Z"


def parse_rfc3339(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
```

`logging.py`:

```python
"""JSON logging to stdout (OBS-001)."""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

from rootline_common.timeutil import to_rfc3339

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
investigation_id_var: ContextVar[str | None] = ContextVar("investigation_id", default=None)


class JsonFormatter(logging.Formatter):
    def __init__(self, component: str) -> None:
        super().__init__()
        self.component = component

    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, object] = {
            "ts": to_rfc3339(datetime.fromtimestamp(record.created, UTC)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "component": self.component,
            "request_id": request_id_var.get(),
        }
        if (inv := investigation_id_var.get()) is not None:
            out["investigation_id"] = inv
        try:
            from opentelemetry import trace

            ctx = trace.get_current_span().get_span_context()
            if ctx.is_valid:
                out["trace_id"] = f"{ctx.trace_id:032x}"
                out["span_id"] = f"{ctx.span_id:016x}"
        except ImportError:
            pass
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, separators=(",", ":"), default=str)


def configure_logging(component: str, level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(component))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
```

`problem.py`:

```python
"""RFC 9457 problem+json (API-002)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rootline_common.ids import new_ulid
from rootline_common.logging import request_id_var

PROBLEM_CODES: dict[str, int] = {
    "unauthenticated": 401, "insufficient_user_authentication": 401, "forbidden": 403,
    "not_found": 404, "validation_error": 422, "invalid_transition": 409, "conflict": 409,
    "separation_of_duties": 403, "rate_limited": 429, "lab_busy": 409, "internal": 500,
}
log = logging.getLogger("rootline.problem")


class Problem(Exception):
    def __init__(self, code: str, status: int, title: str, detail: str = "",
                 extra: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> None:
        super().__init__(detail or title)
        self.code, self.status, self.title, self.detail = code, status, title, detail[:500]
        self.extra, self.headers = extra or {}, headers or {}


def _body(request: Request, code: str, status: int, title: str, detail: str,
          extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": f"https://rootline.dev/problems/{code}", "title": title, "status": status,
            "detail": detail, "instance": request.url.path, "code": code,
            "request_id": request_id_var.get() or new_ulid(), **(extra or {})}


def _resp(body: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(body, status_code=body["status"], media_type="application/problem+json",
                        headers=headers)


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def _problem(request: Request, exc: Problem) -> JSONResponse:
        return _resp(_body(request, exc.code, exc.status, exc.title, exc.detail, exc.extra), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return _resp(_body(request, "validation_error", 422, "Validation error",
                           "request body or query is invalid", {"errors": errors}))

    @app.exception_handler(Exception)
    async def _internal(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return _resp(_body(request, "internal", 500, "Internal error", "unexpected error"))
```

`health.py`:

```python
"""/healthz, /readyz, /metrics (ARC-020)."""
from collections.abc import Awaitable, Callable, Mapping

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def make_health_router(checks: Mapping[str, Callable[[], Awaitable[bool]]]) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/readyz", include_in_schema=False)
    async def readyz() -> JSONResponse:
        failing = []
        for name, check in checks.items():
            try:
                ok = await check()
            except Exception:  # noqa: BLE001 - any failure means not ready
                ok = False
            if not ok:
                failing.append(name)
        return JSONResponse({"failing": failing} if failing else {"status": "ready"},
                            status_code=503 if failing else 200)

    @router.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return router
```

`requestid.py`:

```python
"""X-Request-Id handling (API-004)."""
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rootline_common.ids import is_ulid, new_ulid
from rootline_common.logging import request_id_var


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode()
        rid = incoming if is_ulid(incoming) else new_ulid()
        token = request_id_var.set(rid)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)
```

`settings.py`:

```python
"""Base settings shared by services."""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")
    rootline_env: Literal["local", "gke", "ci", "ci-e2e", "eval", "test"] = "local"
    log_level: str = "INFO"
    database_url: str | None = None
```

`otel.py`:

```python
"""OpenTelemetry tracing setup (OBS-001). No-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""
import os


def setup_tracing(component: str) -> None:
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": f"rootline-{component}"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    HTTPXClientInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
```

FastAPI instrumentation is applied by each service on its app object with `FastAPIInstrumentor.instrument_app(app)` (services do this in their `create_app`).

- [ ] **Step 4: Run the tests**

Run: `uv run pytest libs/py-common/tests -v --cov=rootline_common` → PASS, coverage ≥ 80%.
Run: `uv run mypy libs/py-common` → no errors.

- [ ] **Step 5: Wiki and commit**

Add `wiki/components/` is not needed for libraries; append to `wiki/log.md`: `- [agent] Added rootline_common foundation modules (W1-T07)`.

```bash
git add libs/py-common wiki/log.md uv.lock
git commit -m "feat(py-common): add ids, time, logging, problem+json, health and request-id modules

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---
### Task W1-T08: Create the `rootline-env` repository

**Requirement IDs:** GEN-010, GEN-011, GEN-024, O-1.
**Depends on:** W1-T01. **Branch:** none in `rootline` except the wiki update (`docs/w1-env-repo`).

- [ ] **Step 1 [CONFIRM]: Ask the owner to confirm**, then create the repo:

```bash
gh repo create arkhash0309/rootline-env --private --description "GitOps environment for Rootline. Commits are made by bots."
gh repo clone arkhash0309/rootline-env /home/arkhash0309/projects/rootline-env
```

Set `ROOTLINE_ENV_DIR=/home/arkhash0309/projects/rootline-env` in `.env.local` (run inside WSL; GEN-040).

- [ ] **Step 2: Create the initial files in the clone**

`README.md`:

```markdown
# rootline-env

GitOps environment for Rootline. Commits are made by bots.

- `workload/` — rendered OpenTelemetry Demo manifests for namespace `shop` (tracked by the ArgoCD Application `workload`).
- `.rootline/baseline.json` — the current known-good baseline tag.

Do not edit by hand except through the owner's documented procedures in the `rootline` repository wiki.
```

`.rootline/baseline.json` is written by W1-T09. Commit and push the README only:

```bash
git -C ../rootline-env add README.md
git -C ../rootline-env commit -m "docs: add README

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git -C ../rootline-env push origin main
```

- [ ] **Step 3: Record in the wiki** — add section `## GitOps repositories` to `wiki/runbooks/local-up.md` (repo URL, clone location rule, `ROOTLINE_ENV_DIR`), append to `wiki/log.md`, commit on `docs/w1-env-repo`, open PR.

---

### Task W1-T09: Workload render script

**Requirement IDs:** WKL-001, WKL-002, WKL-003, WKL-010, WKL-011, TST-WKL-001, GEN-011, PG-11, PG-12, LAB-011.
**Depends on:** W1-T02, W1-T08, W1-T16 (`scripts.proc`). **Branch:** `feat/w1-workload-render`.

**Files:**
- Create: `deploy/upstream/otel-demo/values.yaml`, `scripts/render_workload.py`, `scripts/workload_transforms.py`
- Create: `tests/repo/fixtures/otel-demo-mini.yaml` (hand-written excerpt of `helm template` output: Deployments `payment`, `flagd` (with `init-config` initContainer, `flagd-ui` sidecar, `config-rw` emptyDir, `config-ro` volume), `load-generator`; Services `payment`, `flagd`; ConfigMap `flagd-config` with key `demo.flagd.json` containing two flags, one with `defaultVariant: "on"`; one `Secret`; one ServiceAccount)
- Test: `tests/repo/test_workload_render.py`
- Output (in `rootline-env`): `workload/<component>.yaml`, `workload/flagd-config.yaml`, `workload/networkpolicies.yaml`, `.rootline/baseline.json`

**Interfaces:**
- Produces: `scripts.workload_transforms.transform(docs: list[dict]) -> dict[str, list[dict]]` (file stem → objects); `scripts.workload_transforms.dump(objs: list[dict]) -> str`; `uv run python scripts/render_workload.py --out <dir>`; constant `KEPT_COMPONENTS` (the 19 names of WKL-002); `COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"`.

- [ ] **Step 1: Write `deploy/upstream/otel-demo/values.yaml`**

```yaml
# Chart open-telemetry/opentelemetry-demo 0.42.8 (app 3.1.0). WKL-002, WKL-003.
default:
  replicas: 1
components:
  accounting: {enabled: false}
  agent: {enabled: false}
  chatbot: {enabled: false}
  mcp: {enabled: false}
  telemetry-docs: {enabled: false}
  opamp-server: {enabled: false}
  firepit: {enabled: false}
opentelemetry-collector: {enabled: false}
otel-ebpf-profiler: {enabled: false}
jaeger: {enabled: false}
prometheus: {enabled: false}
grafana: {enabled: false}
opensearch: {enabled: false}
```

Kept components (WKL-002) stay at chart defaults.

- [ ] **Step 2: Write the failing tests**

```python
"""Verifies WKL-010, WKL-011 (TST-WKL-001), PG-11, PG-12."""
import json
from pathlib import Path

import yaml

from scripts.workload_transforms import COLLECTOR_FQDN, dump, transform

FIX = Path(__file__).parent / "fixtures/otel-demo-mini.yaml"


def docs() -> list[dict]:
    return [d for d in yaml.safe_load_all(FIX.read_text(encoding="utf-8")) if d]


def test_tst_wkl_001_deterministic() -> None:
    """TST-WKL-001: two renders are byte-identical."""
    a = {k: dump(v) for k, v in transform(docs()).items()}
    b = {k: dump(v) for k, v in transform(docs()).items()}
    assert a == b


def test_namespace_and_no_secrets() -> None:
    out = transform(docs())
    objs = [o for v in out.values() for o in v]
    assert all(o["metadata"]["namespace"] == "shop" for o in objs)
    assert not any(o["kind"] == "Secret" for o in objs)


def test_labels_on_workloads() -> None:
    dep = next(o for o in transform(docs())["payment"] if o["kind"] == "Deployment")
    assert dep["metadata"]["labels"]["app.kubernetes.io/part-of"] == "rootline-workload"
    assert dep["spec"]["template"]["metadata"]["labels"]["rootline.dev/workload"] == "payment"


def test_readiness_probe_added() -> None:
    dep = next(o for o in transform(docs())["payment"] if o["kind"] == "Deployment")
    probe = dep["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
    assert probe == {"tcpSocket": {"port": 8080}, "initialDelaySeconds": 5, "periodSeconds": 10,
                     "failureThreshold": 3}


def test_collector_name_rewritten_ports_kept() -> None:
    dep = next(o for o in transform(docs())["payment"] if o["kind"] == "Deployment")
    env = {e["name"]: e.get("value") for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["OTEL_COLLECTOR_NAME"] == COLLECTOR_FQDN
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://$(OTEL_COLLECTOR_NAME):4317"


def test_flagd_mounts_configmap_directly() -> None:
    out = transform(docs())
    dep = next(o for o in out["flagd"] if o["kind"] == "Deployment")
    spec = dep["spec"]["template"]["spec"]
    assert [c["name"] for c in spec.get("initContainers", [])] == []
    assert [c["name"] for c in spec["containers"]] == ["flagd"]
    vols = {v["name"]: v for v in spec["volumes"]}
    assert vols["config-rw"] == {"name": "config-rw", "configMap": {"name": "flagd-config"}}
    assert "config-ro" not in vols


def test_flags_all_off() -> None:
    cm = transform(docs())["flagd-config"][0]
    flags = json.loads(cm["data"]["demo.flagd.json"])["flags"]
    assert {f["defaultVariant"] for f in flags.values()} == {"off"}


def test_load_generator_env() -> None:
    dep = next(o for o in transform(docs())["load-generator"] if o["kind"] == "Deployment")
    env = {e["name"]: e.get("value") for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert (env["LOCUST_USERS"], env["LOCUST_SPAWN_RATE"], env["LOCUST_AUTOSTART"]) == ("10", "2", "true")


def test_networkpolicies_file() -> None:
    names = [o["metadata"]["name"] for o in transform(docs())["networkpolicies"]]
    assert names == ["allow-observability-scrape", "allow-same-namespace"]
```

Run: `uv run pytest tests/repo/test_workload_render.py -v` → FAIL.

- [ ] **Step 3: Implement `scripts/workload_transforms.py`**

```python
"""Pure transforms for rendered OTel Demo manifests (WKL-010, PG-11, PG-12)."""
from __future__ import annotations

import copy
import json
from typing import Any

import yaml

COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"
KEPT_COMPONENTS = [
    "frontend", "frontend-proxy", "load-generator", "flagd", "ad", "cart", "valkey-cart", "checkout",
    "currency", "email", "payment", "product-catalog", "astronomy-db", "quote", "recommendation",
    "shipping", "kafka", "fraud-detection", "image-provider",
]
WORKLOAD_KINDS = ("Deployment", "StatefulSet")
KIND_ORDER = ["ServiceAccount", "ConfigMap", "Service", "Deployment", "StatefulSet"]


def component_of(obj: dict[str, Any]) -> str:
    labels = obj.get("metadata", {}).get("labels", {}) or {}
    return labels.get("app.kubernetes.io/component") or obj["metadata"]["name"]


def _set_env(container: dict[str, Any], name: str, value: str) -> None:
    for e in container.setdefault("env", []):
        if e["name"] == name:
            e.pop("valueFrom", None)
            e["value"] = value
            return
    container["env"].append({"name": name, "value": value})


def _fix_otel(container: dict[str, Any]) -> None:
    for e in container.get("env", []):
        if e["name"] == "OTEL_COLLECTOR_NAME":
            e["value"] = COLLECTOR_FQDN
        elif e["name"] == "OTEL_EXPORTER_OTLP_ENDPOINT" and "$(OTEL_COLLECTOR_NAME)" not in e.get("value", ""):
            scheme, _, rest = e["value"].partition("://")
            port = rest.rsplit(":", 1)[1] if ":" in rest else "4317"
            e["value"] = f"{scheme}://{COLLECTOR_FQDN}:{port}"


def _add_readiness(container: dict[str, Any]) -> None:
    ports = container.get("ports") or []
    if ports and "readinessProbe" not in container:
        container["readinessProbe"] = {"tcpSocket": {"port": ports[0]["containerPort"]},
                                       "initialDelaySeconds": 5, "periodSeconds": 10, "failureThreshold": 3}


def _fix_flagd(spec: dict[str, Any]) -> None:
    spec.pop("initContainers", None)
    spec["containers"] = [c for c in spec["containers"] if c["name"] == "flagd"]
    vols = [v for v in spec.get("volumes", []) if v["name"] != "config-ro"]
    for v in vols:
        if v["name"] == "config-rw":
            v.clear()
            v.update({"name": "config-rw", "configMap": {"name": "flagd-config"}})
    spec["volumes"] = vols


def _flags_off(cm: dict[str, Any]) -> None:
    data = json.loads(cm["data"]["demo.flagd.json"])
    for flag in data["flags"].values():
        flag["defaultVariant"] = "off"
    cm["data"]["demo.flagd.json"] = json.dumps(data, indent=2, sort_keys=True) + "\n"


def network_policies() -> list[dict[str, Any]]:
    base = {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy"}
    return [
        {**base, "metadata": {"name": "allow-observability-scrape", "namespace": "shop"},
         "spec": {"podSelector": {}, "policyTypes": ["Ingress"], "ingress": [{"from": [{"namespaceSelector": {
             "matchLabels": {"kubernetes.io/metadata.name": "observability"}}}]}]}},
        {**base, "metadata": {"name": "allow-same-namespace", "namespace": "shop"},
         "spec": {"podSelector": {}, "policyTypes": ["Ingress"],
                  "ingress": [{"from": [{"podSelector": {}}]}]}},
    ]


def transform(docs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for original in docs:
        obj = copy.deepcopy(original)
        if obj["kind"] == "Secret":
            continue
        obj["metadata"]["namespace"] = "shop"
        obj["metadata"].pop("managedFields", None)
        if obj["kind"] == "ConfigMap" and obj["metadata"]["name"] == "flagd-config":
            _flags_off(obj)
            out.setdefault("flagd-config", []).append(obj)
            continue
        comp = component_of(obj)
        if comp not in KEPT_COMPONENTS:
            continue
        if obj["kind"] in WORKLOAD_KINDS:
            obj["metadata"].setdefault("labels", {})["app.kubernetes.io/part-of"] = "rootline-workload"
            tmpl = obj["spec"]["template"]
            tmpl.setdefault("metadata", {}).setdefault("labels", {})["rootline.dev/workload"] = comp
            spec = tmpl["spec"]
            if comp == "flagd":
                _fix_flagd(spec)
            for c in spec["containers"] + spec.get("initContainers", []):
                _fix_otel(c)
            for c in spec["containers"]:
                _add_readiness(c)
            if comp == "load-generator":
                for name, value in (("LOCUST_USERS", "10"), ("LOCUST_SPAWN_RATE", "2"),
                                    ("LOCUST_AUTOSTART", "true")):
                    _set_env(spec["containers"][0], name, value)
        out.setdefault(comp, []).append(obj)
    for comp, objs in out.items():
        objs.sort(key=lambda o: (KIND_ORDER.index(o["kind"]) if o["kind"] in KIND_ORDER else 99,
                                 o["metadata"]["name"]))
    out["networkpolicies"] = sorted(network_policies(), key=lambda o: o["metadata"]["name"])
    return out


def dump(objs: list[dict[str, Any]]) -> str:
    return "---\n".join(yaml.safe_dump(o, sort_keys=True, default_flow_style=False) for o in objs)
```

- [ ] **Step 4: Implement `scripts/render_workload.py`**

```python
"""Render the workload into rootline-env (WKL-001). Usage:
  uv run python scripts/render_workload.py --out <rootline-env>/workload
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from scripts.proc import run
from scripts.versions_lib import REPO, load_versions
from scripts.workload_transforms import dump, transform


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    demo = load_versions()["opentelemetry-demo"]
    run(["helm", "repo", "add", "open-telemetry", demo["repo"], "--force-update"])
    rendered = run(["helm", "template", "shop", "open-telemetry/opentelemetry-demo", "--version",
                    demo["chart"], "--namespace", "shop", "-f",
                    str(REPO / "deploy/upstream/otel-demo/values.yaml")]).stdout
    files = transform([d for d in yaml.safe_load_all(rendered) if d])
    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.yaml"):
        stale.unlink()
    for stem, objs in sorted(files.items()):
        (args.out / f"{stem}.yaml").write_text(dump(objs), encoding="utf-8", newline="\n")
    meta = args.out.parent / ".rootline/baseline.json"
    meta.parent.mkdir(exist_ok=True)
    meta.write_text(json.dumps({"baseline_tag": "baseline-v1", "rendered_from": demo["chart"]},
                               sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests** → `uv run pytest tests/repo/test_workload_render.py -v` → PASS.

- [ ] **Step 6: Render for real and verify determinism on real output**

```bash
uv run python scripts/render_workload.py --out "$ROOTLINE_ENV_DIR/workload"
git -C "$ROOTLINE_ENV_DIR" status --porcelain
uv run python scripts/render_workload.py --out "$ROOTLINE_ENV_DIR/workload"
git -C "$ROOTLINE_ENV_DIR" diff --stat   # expected: no changes between the two renders after staging the first
```

Inspect the output and record in `wiki/components/workload.md`: (a) the kind of `astronomy-db` (LAB-011), (b) the kind of `valkey-cart` and `kafka`, (c) the container index of `LOCUST_USERS` in `load-generator` (WKL-041), (d) the env var names in `checkout` and `frontend` used by G02 (LAB-012), (e) every container port per component.

- [ ] **Step 7: Commit both repositories**

In `rootline-env` (direct push is allowed before the W3 ruleset exists):

```bash
git -C "$ROOTLINE_ENV_DIR" add -A
git -C "$ROOTLINE_ENV_DIR" commit -m "feat: render workload from opentelemetry-demo 0.42.8

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git -C "$ROOTLINE_ENV_DIR" tag baseline-v1
git -C "$ROOTLINE_ENV_DIR" push origin main --tags
```

In `rootline`: commit `deploy/upstream/otel-demo/values.yaml`, `scripts/`, tests, `wiki/components/workload.md`, `wiki/log.md` on the feature branch with message `feat(deploy): add deterministic workload render`.

---

### Task W1-T10: k3d cluster config and the ArgoCD app-of-apps

**Requirement IDs:** INF-020, INF-021, INF-022 (helpers stub), INF-030, INF-031, ARC-010, ARC-002, GEN-012, SEC-011 (local CoreDNS), SEC-100 (bootstrap store), PG-9, PG-10.
**Depends on:** W1-T02, W1-T09. **Branch:** `feat/w1-gitops-root`.

**Files:**
- Create: `infra/k3d/rootline.yaml`, `infra/k3d/manifests/traefik-config.yaml`
- Create: `deploy/root/Chart.yaml`, `deploy/root/values.yaml`, `deploy/root/templates/_app.tpl`, `deploy/root/templates/apps.yaml`
- Create: `deploy/charts/namespaces/{Chart.yaml,values.yaml,templates/namespaces.yaml}`
- Create: `deploy/charts/platform-config/{Chart.yaml,values.yaml,templates/*.yaml}` (cluster issuers and CA, ESO stores and generators, `coredns-custom`, Gateway, `rootline-ca` ConfigMap; Kyverno policies are added in W3-T12)
- Create: `deploy/charts/rootline/{Chart.yaml,values.yaml,templates/_helpers.tpl}` (empty umbrella with helpers)
- Create: `deploy/upstream/<name>/values-local.yaml` for `argo-cd`, `cert-manager`, `external-secrets`, `cloudnative-pg`, `kyverno`, `chaos-mesh`, `gateway-api` (README only), and `deploy/upstream/README.md` listing every upstream chart repo (SEC-110 `rootline-platform` sources)
- Create: `scripts/render_manifests.py` (renders `deploy/root` for `local`, `gke`, `ci` and every chart with each env values file, to stdout as one YAML stream; used by lint and CI)
- Test: `tests/repo/test_root_chart.py`

**Interfaces:**
- Produces: root chart values contract used by every later wave:

```yaml
# deploy/root/values.yaml
env: local                      # local | gke | ci
domain: 127.0.0.1.sslip.io
targetRevision: develop
repoURL: git@github.com:arkhash0309/rootline.git
envRepoURL: git@github.com:arkhash0309/rootline-env.git
envRepoRevision: main
gcpProject: ""
k8sIssuer: https://kubernetes.default.svc.cluster.local
artifactsBucket: ""
ingressIP: ""
apps:                           # every Application; later tasks flip enabled: true
  namespaces:        {enabled: true,  wave: -4, kind: local-chart, path: deploy/charts/namespaces}
  gateway-api-crds:  {enabled: true,  wave: -4, kind: url, versionKey: gateway-api}
  cert-manager:      {enabled: true,  wave: -3, kind: upstream, versionKey: cert-manager, chart: cert-manager, namespace: cert-manager}
  external-secrets:  {enabled: true,  wave: -3, kind: upstream, versionKey: external-secrets, chart: external-secrets, namespace: external-secrets}
  cnpg-operator:     {enabled: true,  wave: -3, kind: upstream, versionKey: cloudnative-pg, chart: cloudnative-pg, namespace: cnpg-system}
  kyverno:           {enabled: true,  wave: -3, kind: upstream, versionKey: kyverno, chart: kyverno, namespace: kyverno}
  chaos-mesh:        {enabled: true,  wave: -3, kind: upstream, versionKey: chaos-mesh, chart: chaos-mesh, namespace: chaos-mesh, envs: [local]}
  prometheus-crds:   {enabled: true,  wave: -3, kind: upstream, versionKey: kube-prometheus-stack, chart: prometheus-operator-crds, namespace: observability}
  traefik:           {enabled: true,  wave: -3, kind: upstream, versionKey: traefik, chart: traefik, namespace: traefik, envs: [gke]}
  platform-config:   {enabled: true,  wave: -2, kind: local-chart, path: deploy/charts/platform-config}
  postgres:          {enabled: true,  wave: -1, kind: local-chart, path: deploy/charts/postgres}
  observability:     {enabled: true,  wave: -1, kind: local-chart, path: deploy/charts/observability}
  keycloak:          {enabled: false, wave: 0,  kind: local-chart, path: deploy/charts/keycloak}
  argocd-accounts:   {enabled: false, wave: 0,  kind: local-chart, path: deploy/charts/argocd-accounts}
  rootline:          {enabled: true,  wave: 1,  kind: local-chart, path: deploy/charts/rootline}
  workload:          {enabled: true,  wave: 2,  kind: env-repo, path: workload}
  demo-seed:         {enabled: false, wave: 2,  kind: local-chart, path: deploy/charts/demo-seed, envs: [gke]}
```

(`prometheus-crds` uses chart `prometheus-community/prometheus-operator-crds`; the key `prometheus-operator-crds` is resolved by W1-T02. `observability` is a local wrapper chart with upstream dependencies, created in W1-T11.)

- Every local chart receives Helm parameters `global.env`, `global.domain`, `global.gcpProject`, `global.k8sIssuer`, `global.artifactsBucket`, `global.ingressIP` and its `values-<env>.yaml` file (`valueFiles: [values.yaml, values-<env>.yaml]`, `ignoreMissingValueFiles: true`).

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies INF-020, INF-021, GEN-012, ARC-010."""
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


def render(env: str) -> list[dict]:
    out = subprocess.run(["helm", "template", "root", str(REPO / "deploy/root"), "--set", f"env={env}"],
                         check=True, capture_output=True, text=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


@pytest.mark.parametrize("env", ["local", "gke", "ci"])
def test_waves_and_sync_policy(env: str) -> None:
    apps = {a["metadata"]["name"]: a for a in render(env)}
    assert apps["namespaces"]["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-4"
    assert apps["rootline"]["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "1"
    for name, a in apps.items():
        sp = a["spec"]["syncPolicy"]
        if name == "workload":
            assert sp["automated"] == {"prune": True, "selfHeal": False}
            # W2-T08 tightens this to == "rootline-workload" when the AppProject exists.
            assert a["spec"]["project"] in {"default", "rootline-workload"}
        else:
            assert sp["automated"] == {"prune": True, "selfHeal": True}
            assert sp["syncOptions"] == ["CreateNamespace=false", "ServerSideApply=true"]


def test_env_filters() -> None:
    assert "chaos-mesh" in {a["metadata"]["name"] for a in render("local")}
    assert "chaos-mesh" not in {a["metadata"]["name"] for a in render("gke")}
    assert "traefik" in {a["metadata"]["name"] for a in render("gke")}
    assert "traefik" not in {a["metadata"]["name"] for a in render("local")}


def test_workload_ignores_load_generator_env() -> None:
    wl = next(a for a in render("local") if a["metadata"]["name"] == "workload")
    assert {"group": "apps", "kind": "Deployment", "name": "load-generator",
            "jsonPointers": ["/spec/template/spec/containers/0/env"]} in wl["spec"]["ignoreDifferences"]


def test_namespaces_pss() -> None:
    out = subprocess.run(["helm", "template", "ns", str(REPO / "deploy/charts/namespaces")],
                         check=True, capture_output=True, text=True).stdout
    ns = {d["metadata"]["name"]: d["metadata"]["labels"] for d in yaml.safe_load_all(out) if d}
    expected = {"rootline": "restricted", "rootline-data": "restricted", "rootline-lab": "restricted",
                "rootline-secrets": "restricted", "keycloak": "restricted", "observability": "baseline",
                "shop": "baseline", "argocd": "baseline", "chaos-mesh": "privileged", "kyverno": "baseline",
                "external-secrets": "baseline", "cert-manager": "baseline", "cnpg-system": "baseline",
                "traefik": "baseline"}
    for name, level in expected.items():
        assert ns[name]["pod-security.kubernetes.io/enforce"] == level, name
```

Run: `uv run pytest tests/repo/test_root_chart.py -v` → FAIL.

- [ ] **Step 2: Write `infra/k3d/rootline.yaml` and Traefik config** — exactly INF-030 (with `image: rancher/k3s:<versions.k3s with + replaced by ->`; `scripts/up.py` substitutes it at runtime by writing `infra/k3d/rootline.generated.yaml`, gitignored) and:

```yaml
# infra/k3d/manifests/traefik-config.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata: {name: traefik, namespace: kube-system}
spec:
  valuesContent: |-
    deployment:
      replicas: 1
    providers:
      kubernetesGateway:
        enabled: true
    ports:
      websecure:
        tls:
          enabled: true
```

- [ ] **Step 3: Write the root chart**

`deploy/root/Chart.yaml`: `apiVersion: v2`, `name: rootline-root`, `version: 0.1.0`, `type: application`.

`deploy/root/templates/apps.yaml`:

```yaml
{{- $versions := .Files.Get "files/versions.yaml" | fromYaml }}
{{- range $name, $app := .Values.apps }}
{{- if and $app.enabled (or (not $app.envs) (has $.Values.env $app.envs)) }}
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {{ $name }}
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: {{ $app.wave | quote }}
  finalizers: [resources-finalizer.argocd.argoproj.io]
spec:
  project: {{ if and (eq $app.kind "env-repo") (index $.Values.apps "argocd-accounts").enabled }}rootline-workload{{ else }}default{{ end }}
  destination:
    server: https://kubernetes.default.svc
    namespace: {{ $app.namespace | default (ternary "shop" "argocd" (eq $app.kind "env-repo")) }}
  {{- if eq $app.kind "local-chart" }}
  source:
    repoURL: {{ $.Values.repoURL }}
    targetRevision: {{ $.Values.targetRevision }}
    path: {{ $app.path }}
    helm:
      valueFiles: [values.yaml, values-{{ $.Values.env }}.yaml]
      ignoreMissingValueFiles: true
      parameters:
        - {name: global.env, value: {{ $.Values.env | quote }}}
        - {name: global.domain, value: {{ $.Values.domain | quote }}}
        - {name: global.gcpProject, value: {{ $.Values.gcpProject | quote }}}
        - {name: global.k8sIssuer, value: {{ $.Values.k8sIssuer | quote }}}
        - {name: global.artifactsBucket, value: {{ $.Values.artifactsBucket | quote }}}
        - {name: global.ingressIP, value: {{ $.Values.ingressIP | quote }}}
  {{- else if eq $app.kind "upstream" }}
  {{- $v := index $versions $app.versionKey }}
  sources:
    - repoURL: {{ $v.repo }}
      chart: {{ $app.chart }}
      targetRevision: {{ $v.chart | quote }}
      helm:
        valueFiles:
          - $values/deploy/upstream/{{ $name }}/values-{{ $.Values.env }}.yaml
        ignoreMissingValueFiles: true
    - repoURL: {{ $.Values.repoURL }}
      targetRevision: {{ $.Values.targetRevision }}
      ref: values
  {{- else if eq $app.kind "url" }}
  {{- $v := index $versions $app.versionKey }}
  source:
    repoURL: https://github.com/kubernetes-sigs/gateway-api
    targetRevision: {{ $v.version }}
    path: config/crd/standard
  {{- else if eq $app.kind "env-repo" }}
  source:
    repoURL: {{ $.Values.envRepoURL }}
    targetRevision: {{ $.Values.envRepoRevision }}
    path: {{ $app.path }}
  ignoreDifferences:
    - group: apps
      kind: Deployment
      name: load-generator
      jsonPointers: [/spec/template/spec/containers/0/env]
  {{- end }}
  syncPolicy:
    automated:
      prune: true
      selfHeal: {{ ne $app.kind "env-repo" }}
    {{- if ne $app.kind "env-repo" }}
    syncOptions: [CreateNamespace=false, ServerSideApply=true]
    {{- end }}
{{- end }}
{{- end }}
```

The AppProject `rootline-workload` (SEC-110) is created by the `argocd-accounts` chart in W2-T08. Until that app is enabled, the `workload` Application uses project `default` (the `project:` line above implements this).

If the container index from W1-T09 step 6(c) is not 0, change the `jsonPointers` value and the test.

- [ ] **Step 4: Write `deploy/charts/namespaces`** — one `Namespace` per row of ARC-010 plus `cnpg-system` and `traefik`, each with labels `pod-security.kubernetes.io/enforce: <level>`, `pod-security.kubernetes.io/enforce-version: latest`, `rootline.dev/managed: "true"`. Default-deny NetworkPolicies for the namespaces marked "yes" in ARC-010 (`rootline`, `rootline-data`, `rootline-lab`, `rootline-secrets`, `keycloak`, `observability`): `podSelector: {}`, `policyTypes: [Ingress, Egress]`, plus an `allow-dns` egress policy to `kube-system` port 53 UDP/TCP. Allow-rules for each flow are added by the charts that own the pods (W1-T11 for observability and postgres, W3-T12 for `rootline`, W3-T01 for keycloak). Exception for week 1: `observability` and `rootline-data` get their allow-rules in W1-T11.

- [ ] **Step 5: Write `deploy/charts/platform-config`**

Templates (each gated by `.Values.global.env` where noted):

| File | Objects |
|---|---|
| `ca.yaml` | (local, ci) `ClusterIssuer selfsigned` (`selfSigned: {}`); `Certificate rootline-local-ca` in `cert-manager` (`isCA: true`, `duration: 87600h`, `privateKey: {algorithm: ECDSA, size: 256}`, `secretName: rootline-local-ca`, `issuerRef: selfsigned`); `ClusterIssuer rootline-ca` (`ca.secretName: rootline-local-ca`); `Certificate rootline-wildcard` in `kube-system` for `*.{{ .Values.global.domain }}` and `{{ .Values.global.domain }}` from `rootline-ca`, secret `rootline-wildcard-tls` |
| `gateway.yaml` | `Gateway rootline` in `kube-system` (local/ci; `traefik` ns on gke), `gatewayClassName: traefik`, listeners `http` (80, `allowedRoutes.namespaces.from: All`) and `https` (443, TLS terminate with `rootline-wildcard-tls`, `allowedRoutes.namespaces.from: All`) |
| `coredns.yaml` | (local, ci) `ConfigMap coredns-custom` in `kube-system` with key `rootline.override`: `rewrite name auth.{{D}} traefik.kube-system.svc.cluster.local` and the same for `console.{{D}}` and `argocd.{{D}}` |
| `ca-configmap.yaml` | `ConfigMap rootline-ca` in `rootline` and `keycloak` with key `ca.crt`. trust-manager is not installed, so a PostSync Job `copy-ca` (image `bitnami/kubectl`, pinned by digest in `versions.yaml` as `kubectl-image`) reads secret `cert-manager/rootline-local-ca` key `ca.crt` and applies the ConfigMap to both namespaces. RBAC: ServiceAccount `copy-ca` in `cert-manager`; Role in `cert-manager` with `get` on secret `rootline-local-ca`; Roles in `rootline` and `keycloak` with `get,create,patch` on configmaps (`resourceNames: [rootline-ca]` for `get,patch`; `create` cannot be restricted by name) |
| `eso-bootstrap.yaml` | (local, ci) ServiceAccount `eso-bootstrap-reader` in `rootline-secrets`; Role `get,list,watch` on secrets named `rootline-bootstrap`; `ClusterSecretStore bootstrap` (`provider.kubernetes.remoteNamespace: rootline-secrets`, `auth.serviceAccount: {name: eso-bootstrap-reader, namespace: rootline-secrets}`, `server.caProvider: {type: ConfigMap, name: kube-root-ca.crt, key: ca.crt, namespace: rootline-secrets}`) |
| `eso-pg-roles.yaml` | ServiceAccount `eso-pg-reader` in `rootline-data`, Role `get,list,watch` on secrets with names `pg-rootline-migrator`, `pg-rootline-api`, `pg-rootline-agent`, `pg-rootline-faultlab`, `pg-rootline-console`, `pg-keycloak`; `ClusterSecretStore pg-roles` with `remoteNamespace: rootline-data` (PG-10) |
| `generators.yaml` | `Password` generators (`generators.external-secrets.io/v1alpha1`): `password-48` (`length: 48, digits: 8, symbols: 0, noUpper: false, allowRepeat: true`) for passwords and webhook tokens; `password-43` (`length: 43, digits: 8, symbols: 0, allowRepeat: true`) for `job-token-key` and `bff-session-key`. Consumers derive the 32-byte AES key as `sha256(value)`; W4-T06 records this in `wiki/components/api.md` |

For every DB role, an `ExternalSecret pg-<role>` in `rootline-data` with `dataFrom: [{sourceRef: {generatorRef: {apiVersion: generators.external-secrets.io/v1alpha1, kind: Password, name: password-48}}}]`, `refreshInterval: "0"`, and `target.template` producing `type: kubernetes.io/basic-auth` with `username: <role>` and `password: "{{ .password }}"`.

- [ ] **Step 6: Write the empty umbrella chart and helpers**

`deploy/charts/rootline/templates/_helpers.tpl` defines, for later tasks: `rootline.podSecurityContext` (`runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001, seccompProfile: {type: RuntimeDefault}`), `rootline.containerSecurityContext` (`readOnlyRootFilesystem: true, allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}`), `rootline.image` (`{{ .Values.image.registry }}/{{ .component }}:{{ .Values.image.tag }}`), `rootline.probes` (`/healthz` liveness period 10 s, `/readyz` readiness period 5 s, both on port `http`), `rootline.otelEnv` (`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317`, `OTEL_SERVICE_NAME=rootline-<component>`), `rootline.keycloakTokenVolume` (projected SA token per SEC-033). `values.yaml`: `image: {registry: rootline, tag: dev, pullPolicy: IfNotPresent}`, `resources:` map per component from ARC-030, `security: {delegationMode: act}`, `llm: {clusterBudgetUsd: 6}`. `values-gke.yaml`: `image.registry: us-central1-docker.pkg.dev/{{gcpProject}}/rootline`, `image.pullPolicy: IfNotPresent`. No templates yet render objects.

- [ ] **Step 7: Upstream values for week 1** (`deploy/upstream/<name>/values-local.yaml`; copy to `values-ci.yaml` and `values-gke.yaml` with the differences noted)

| Chart | Values (local) |
|---|---|
| `argo-cd` | `dex.enabled: false`, `notifications.enabled: false`, `applicationSet.replicas: 0`, `configs.params."server.insecure": true`, `configs.cm."admin.enabled": true`, `configs.cm."accounts.rootline-gate": apiKey`, `configs.cm."accounts.rootline-faultlab": apiKey`, `server.resources.requests.memory: 160Mi`, `repoServer.resources.requests.memory: 192Mi`, `controller.resources.requests.memory: 224Mi`, `redis.resources.requests.memory: 64Mi` (sum 640 Mi per ARC-030; limits sum 1.2 Gi) |
| `cert-manager` | `crds.enabled: true`; requests 48Mi controller, 40Mi webhook, 40Mi cainjector |
| `external-secrets` | `installCRDs: true`, `webhook.create: true`, `certController.create: true`, requests 32Mi each (controller 32Mi, others 16Mi) |
| `cloudnative-pg` | `resources.requests.memory: 96Mi`, `limits.memory: 256Mi` |
| `kyverno` | `admissionController.replicas: 1`, `backgroundController.replicas: 1`, `cleanupController.enabled: false`, `reportsController.enabled: false`; requests 160Mi admission, 96Mi background |
| `chaos-mesh` | `chaosDaemon.runtime: containerd`, `chaosDaemon.socketPath: /run/k3s/containerd/containerd.sock`, `dnsServer.create: true`, `dashboard.create: false`, `controllerManager.replicaCount: 1`, requests 128Mi controller, 96Mi daemon, 32Mi dns |

`gke` copy differences: `chaos-mesh` not deployed on gke (root values `envs: [local]`); `argo-cd` identical; others identical.

- [ ] **Step 8: Implement `scripts/render_manifests.py`** — for each env in `local`, `gke`, `ci`: `helm template` the root chart; for every Application of kind `local-chart`, run `helm template` on that chart path with `values.yaml` and `values-<env>.yaml` (if present) and `--set global.env=<env> --set global.domain=example.sslip.io`; print all documents to stdout separated by `---`. Exit non-zero on any helm failure.

- [ ] **Step 9: Run tests and lint**

Run: `uv run pytest tests/repo/test_root_chart.py -v` → PASS.
Run: `uv run python scripts/render_manifests.py | kubeconform -strict -summary -ignore-missing-schemas -schema-location default -schema-location "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"` → 0 invalid.

- [ ] **Step 10: Wiki and commit** — create/update `wiki/components/argocd.md`, `cert-manager.md`, `external-secrets.md`, `traefik.md`, `kyverno.md` (installed; no policies yet), `chaos-mesh.md` with WIK-010 sections; log entry. Commit `feat(deploy): add k3d config and ArgoCD app-of-apps`.

---

### Task W1-T11: Observability stack and Postgres

**Requirement IDs:** WKL-020, WKL-021, WKL-022, WKL-023, ARC-002, ARC-030, DB-001, DB-002 (roles), PG-10.
**Depends on:** W1-T10. **Branch:** `feat/w1-observability-postgres`.

**Files:**
- Create: `deploy/charts/observability/Chart.yaml` (dependencies: `kube-prometheus-stack`, `loki`, `tempo`, `opentelemetry-collector`, versions from `versions.yaml` — `scripts/render_versions.py` gains a step that rewrites the `dependencies` versions in this `Chart.yaml` and `--check` covers it), `values.yaml`, `values-local.yaml`, `values-gke.yaml`, `values-ci.yaml`, `templates/networkpolicies.yaml`
- Create: `deploy/charts/postgres/{Chart.yaml,values.yaml,values-gke.yaml,templates/cluster.yaml,templates/database-keycloak.yaml,templates/networkpolicies.yaml}`
- Test: `tests/repo/test_observability_values.py`

- [ ] **Step 1: Write the failing test**

```python
"""Verifies WKL-020, WKL-021, WKL-023, DB-001, DB-002."""
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def tmpl(chart: str, env: str) -> list[dict]:
    args = ["helm", "template", "x", str(REPO / f"deploy/charts/{chart}"), "-f",
            str(REPO / f"deploy/charts/{chart}/values.yaml"), "--set", f"global.env={env}"]
    f = REPO / f"deploy/charts/{chart}/values-{env}.yaml"
    if f.exists():
        args += ["-f", str(f)]
    subprocess.run(["helm", "dependency", "build", str(REPO / f"deploy/charts/{chart}")], check=True)
    return [d for d in yaml.safe_load_all(subprocess.run(args, check=True, capture_output=True,
                                                         text=True).stdout) if d]


def test_prometheus_otlp_and_retention() -> None:
    prom = next(d for d in tmpl("observability", "local") if d["kind"] == "Prometheus")
    assert "otlp-write-receiver" in prom["spec"].get("enableFeatures", []) or \
        prom["spec"].get("enableOTLPReceiver") is True
    assert prom["spec"]["retention"] == "2d"
    assert set(prom["spec"]["otlp"]["promoteResourceAttributes"]) >= {
        "service.name", "k8s.namespace.name", "k8s.pod.name"}
    assert prom["spec"]["scrapeInterval"] == "15s"


def test_gke_retention() -> None:
    prom = next(d for d in tmpl("observability", "gke") if d["kind"] == "Prometheus")
    assert prom["spec"]["retention"] == "1d"


def test_no_grafana() -> None:
    kinds = {(d["kind"], d["metadata"]["name"]) for d in tmpl("observability", "local")}
    assert not any("grafana" in n for _, n in kinds)


def test_cnpg_cluster() -> None:
    c = next(d for d in tmpl("postgres", "local") if d["kind"] == "Cluster")
    assert c["metadata"] == {"name": "rootline-pg", "namespace": "rootline-data"} | {
        k: v for k, v in c["metadata"].items() if k not in ("name", "namespace")}
    assert c["spec"]["instances"] == 1 and c["spec"]["storage"]["size"] == "5Gi"
    assert c["spec"]["postgresql"]["parameters"] == {
        "shared_buffers": "128MB", "max_connections": "100", "log_min_duration_statement": "500"}
    roles = {r["name"] for r in c["spec"]["managed"]["roles"]}
    assert roles == {"rootline_migrator", "rootline_api", "rootline_agent", "rootline_faultlab",
                     "rootline_console", "keycloak"}
    assert c["spec"]["bootstrap"]["initdb"] == {"database": "rootline", "owner": "rootline_migrator",
                                                "secret": {"name": "pg-rootline-migrator"}}
```

Run → FAIL.

- [ ] **Step 2: Observability values** (`deploy/charts/observability/values.yaml`, keys nested under each dependency name)

```yaml
kube-prometheus-stack:
  grafana: {enabled: false}
  nodeExporter: {enabled: false}
  crds: {enabled: false}            # installed by the prometheus-crds Application (wave -3)
  defaultRules: {create: false}
  kubeStateMetrics: {enabled: true}
  kube-state-metrics:
    resources: {requests: {memory: 64Mi}, limits: {memory: 192Mi}}
  prometheusOperator:
    resources: {requests: {memory: 96Mi}, limits: {memory: 192Mi}}
  alertmanager:
    alertmanagerSpec:
      resources: {requests: {memory: 48Mi}, limits: {memory: 128Mi}}
  prometheus:
    prometheusSpec:
      scrapeInterval: 15s
      retention: 2d
      enableOTLPReceiver: true
      otlp:
        promoteResourceAttributes: [service.name, k8s.namespace.name, k8s.pod.name, k8s.deployment.name]
      enableRemoteWriteReceiver: true          # Tempo metrics-generator remote_write
      serviceMonitorSelectorNilUsesHelmValues: false
      podMonitorSelectorNilUsesHelmValues: false
      ruleSelectorNilUsesHelmValues: false
      resources: {requests: {memory: 768Mi}, limits: {memory: 1536Mi}}
loki:
  deploymentMode: SingleBinary
  loki:
    auth_enabled: false
    commonConfig: {replication_factor: 1}
    storage: {type: filesystem}
    schemaConfig:
      configs: [{from: "2024-04-01", store: tsdb, object_store: filesystem, schema: v13,
                 index: {prefix: index_, period: 24h}}]
    limits_config: {retention_period: 48h, allow_structured_metadata: true}
    compactor: {retention_enabled: true, delete_request_store: filesystem}
  singleBinary:
    replicas: 1
    resources: {requests: {memory: 256Mi}, limits: {memory: 512Mi}}
  read: {replicas: 0}
  write: {replicas: 0}
  backend: {replicas: 0}
  gateway: {enabled: false}
  chunksCache: {enabled: false}
  resultsCache: {enabled: false}
  lokiCanary: {enabled: false}
  test: {enabled: false}
tempo:
  tempo:
    retention: 48h
    metricsGenerator:
      enabled: true
      remoteWriteUrl: http://prometheus-operated.observability.svc:9090/api/v1/write
    overrides:
      defaults:
        metrics_generator:
          processors: [service-graphs, span-metrics]
    resources: {requests: {memory: 384Mi}, limits: {memory: 768Mi}}
opentelemetry-collector:
  mode: daemonset
  image: {repository: otel/opentelemetry-collector-contrib}
  presets:
    kubernetesAttributes: {enabled: true}
    logsCollection: {enabled: true, includeCollectorLogs: false}
  resources: {requests: {memory: 192Mi}, limits: {memory: 384Mi}}
  config:
    receivers:
      otlp: {protocols: {grpc: {endpoint: "0.0.0.0:4317"}, http: {endpoint: "0.0.0.0:4318"}}}
      filelog:
        include: [/var/log/pods/shop_*/*/*.log, /var/log/pods/rootline_*/*/*.log]
    processors:
      memory_limiter: {check_interval: 1s, limit_percentage: 80, spike_limit_percentage: 20}
      batch: {}
    exporters:
      otlp/tempo: {endpoint: "tempo.observability.svc:4317", tls: {insecure: true}}
      otlphttp/prometheus: {endpoint: "http://prometheus-operated.observability.svc:9090/api/v1/otlp",
                            tls: {insecure: true}}
      otlphttp/loki: {endpoint: "http://loki.observability.svc:3100/otlp", tls: {insecure: true}}
    service:
      pipelines:
        traces: {receivers: [otlp], processors: [memory_limiter, k8sattributes, batch], exporters: [otlp/tempo]}
        metrics: {receivers: [otlp], processors: [memory_limiter, k8sattributes, batch],
                  exporters: [otlphttp/prometheus]}
        logs: {receivers: [otlp, filelog], processors: [memory_limiter, k8sattributes, batch],
               exporters: [otlphttp/loki]}
```

The collector Service must be named `otel-collector` (set `fullnameOverride: otel-collector`). The `filelog` preset adds a `hostPath` mount of `/var/log/pods` read-only, which the W3-T12 Kyverno policy explicitly allows. Exact key names for `enableOTLPReceiver`/`otlp` depend on the resolved kube-prometheus-stack version: check `helm show values prometheus-community/kube-prometheus-stack --version <v> | grep -n -i otlp` and adapt; the test accepts either the field or the feature flag.

`values-gke.yaml`: `kube-prometheus-stack.prometheus.prometheusSpec.retention: 1d`, `loki.loki.limits_config.retention_period: 24h`, `tempo.tempo.retention: 24h`, collector `mode: daemonset` unchanged.
`values-ci.yaml`: `loki`, `tempo`, `opentelemetry-collector` disabled with `loki.enabled: false`, `tempo.enabled: false` and `opentelemetry-collector.enabled: false` (add `condition: <name>.enabled` to each of the three dependencies in `Chart.yaml`), Prometheus retention `6h`.

`templates/networkpolicies.yaml`: in `observability`, allow ingress from all namespaces to ports 4317, 4318 (collector), 9090 (Prometheus, from `rootline` and `observability`), 3100 and 3200 (from `rootline` and `observability`), 9093 (Alertmanager, from `observability`); allow egress from `observability` to all namespaces (scraping) and to the kube-apiserver (port 443/6443).

- [ ] **Step 3: Postgres chart** (`deploy/charts/postgres/templates/cluster.yaml`)

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: rootline-pg
  namespace: rootline-data
spec:
  instances: 1
  imageName: ghcr.io/cloudnative-pg/postgresql:16
  storage:
    size: 5Gi
    storageClass: {{ ternary "standard-rwo" "local-path" (eq .Values.global.env "gke") }}
  resources:
    requests: {memory: 384Mi}
    limits: {memory: 768Mi}
  postgresql:
    parameters:
      shared_buffers: 128MB
      max_connections: "100"
      log_min_duration_statement: "500"
  bootstrap:
    initdb:
      database: rootline
      owner: rootline_migrator
      secret: {name: pg-rootline-migrator}
  managed:
    roles:
    {{- range list "rootline_api" "rootline_agent" "rootline_faultlab" "rootline_console" "keycloak" "rootline_migrator" }}
      - name: {{ . }}
        ensure: present
        login: true
        passwordSecret: {name: pg-{{ . | replace "_" "-" }}}
    {{- end }}
```

`database-keycloak.yaml`: CNPG `Database` resource `keycloak` (owner `keycloak`, cluster `rootline-pg`). `networkpolicies.yaml`: ingress to port 5432 from namespaces `rootline` and `keycloak`, plus from the CNPG operator namespace `cnpg-system` to ports 8000 and 5432. Pin `imageName` with the digest resolved in W1-T02 (`versions.yaml` key `postgres-image`).

- [ ] **Step 4: Run tests** → `uv run pytest tests/repo/test_observability_values.py -v` → PASS.

- [ ] **Step 5: Wiki and commit** — pages `kube-prometheus-stack.md`, `loki.md`, `tempo.md`, `otel-collector.md`, `postgres.md`; commit `feat(deploy): add observability stack and CNPG Postgres`.

---

### Task W1-T12: `task up` bring-up and memory budget

**Requirement IDs:** GEN-060 (`up`, `secrets:local`, `trust-ca`, `images`), S2, ARC-030, ARC-031, DB-001 (pgvector check), O-2, O-4.
**Depends on:** W1-T10, W1-T11, O-2, O-4. **Branch:** `feat/w1-task-up`.

**Files:**
- Create: `scripts/up.py`, `scripts/secrets_local.py`, `scripts/trust_ca.py`, `scripts/build_images.py`, `scripts/wait_apps.py`
- Modify: `wiki/runbooks/local-up.md`, `wiki/components/capacity.md`
- Test: `tests/repo/test_up_helpers.py`

**Interfaces:**
- Produces: `scripts.wait_apps.wait_all(context: str, timeout_s: int) -> list[str]` (returns names not Synced/Healthy); `scripts.secrets_local.build_bootstrap_secret(env: dict[str,str]) -> dict` (Secret manifest with every non-empty `.env.local` key except `DEPLOY_KEY_*`, `ROOTLINE_ENV_DIR`, `ROOTLINE_HOST_ANTHROPIC_API_KEY`, `HF_USER`); `scripts.secrets_local.repo_secret(name: str, url: str, key_pem: str) -> dict`; `scripts.build_images.SERVICES` (list of image names that have a `Dockerfile`).

- [ ] **Step 1: Tests**

```python
"""Verifies GEN-060 (secrets:local), PG-9."""
import base64

from scripts.secrets_local import build_bootstrap_secret, repo_secret


def test_bootstrap_secret_excludes_host_only_keys() -> None:
    s = build_bootstrap_secret({"ANTHROPIC_API_KEY": "k", "DEPLOY_KEY_ROOTLINE": "p",
                                "ROOTLINE_HOST_ANTHROPIC_API_KEY": "h", "HF_USER": "u", "EMPTY": ""})
    assert s["metadata"] == {"name": "rootline-bootstrap", "namespace": "rootline-secrets"}
    assert set(s["data"]) == {"ANTHROPIC_API_KEY"}
    assert base64.b64decode(s["data"]["ANTHROPIC_API_KEY"]) == b"k"


def test_repo_secret_shape() -> None:
    s = repo_secret("deploy-key-rootline", "git@github.com:arkhash0309/rootline.git", "PEM")
    assert s["metadata"]["labels"] == {"argocd.argoproj.io/secret-type": "repository"}
    assert s["metadata"]["namespace"] == "argocd"
    assert s["stringData"] == {"type": "git", "url": "git@github.com:arkhash0309/rootline.git",
                               "sshPrivateKey": "PEM"}
```

- [ ] **Step 2: Implement `secrets_local.py`** — builds both manifests and applies them with `kubectl --context k3d-rootline apply -f -` (via `scripts.proc.run(..., input_text=yaml.safe_dump(...))`). Namespaces `rootline-secrets` and `argocd` are created with `kubectl create namespace --dry-run=client -o yaml | kubectl apply -f -` equivalents in Python (build the Namespace manifest and apply) when missing.

- [ ] **Step 3: Implement `up.py`** — steps in order, each printing `==> <step>`:
  1. `k3d cluster list -o json`; if `rootline` absent, write `infra/k3d/rootline.generated.yaml` (substitute `<versions.k3s>` with the tag where `+` becomes `-`, and `<repo>` with the absolute repository path inside WSL, `/home/arkhash0309/projects/rootline`) and run `k3d cluster create --config infra/k3d/rootline.generated.yaml`.
  2. `scripts/build_images.py --tag dev --import-k3d rootline` (skips when no service has a Dockerfile yet).
  3. `helm repo add argo <repo>` and `helm upgrade --install argocd argo/argo-cd --version <chart> -n argocd --create-namespace -f deploy/upstream/argo-cd/values-local.yaml --wait --timeout 10m`.
  4. `scripts/secrets_local.py`.
  5. Render `deploy/root` with `--set env=local,domain=127.0.0.1.sslip.io,targetRevision=<--revision>` and apply as Application `root` (project `default`, source `deploy/root`, those parameters, automated sync with prune and selfHeal) with `kubectl apply`.
  6. `scripts/wait_apps.py --timeout 1200`; on timeout print the unhealthy apps with `kubectl -n argocd get applications` output and exit 1.
  7. Print the ArgoCD admin password from secret `argocd/argocd-initial-admin-secret` key `password` and the URLs `https://argocd.127.0.0.1.sslip.io`.
  8. Run `scripts/doctor.py` memory check and print `memory_requests_total`.

`trust_ca.py`: reads secret `cert-manager/rootline-local-ca` key `ca.crt` (or with `--env gke` the GKE fallback CA secret named in INF-041), writes it to `data/rootline-ca.crt`, then (GEN-060, PG-17): (1) `sudo install -m 0644 data/rootline-ca.crt /usr/local/share/ca-certificates/rootline-ca.crt && sudo update-ca-certificates` (prompts for the sudo password in the terminal); (2) `certutil -d sql:$HOME/.pki/nssdb -A -t C,, -n rootline-local-ca -i data/rootline-ca.crt` after creating the database with `certutil -d sql:$HOME/.pki/nssdb -N --empty-password` if absent; (3) `/mnt/c/Windows/System32/certutil.exe -user -addstore Root <wslpath -w data/rootline-ca.crt>` through WSL interop (absolute path: `appendWindowsPath=false`) (Windows shows a confirmation dialog the owner accepts). Each step prints `OK`/`FAIL`; the script exits 1 if any failed. It refuses to run outside WSL (no `WSL_DISTRO_NAME`) unless `--linux-only` is passed (CI uses `--linux-only`, which skips step 3).

`build_images.py`: `--tag <t>`, `--import-k3d <cluster>` or `--load-kind <cluster>` or `--push <registry>`; image list = every `services/*/Dockerfile` (image name = directory name) plus `apps/console/Dockerfile` (`console`); build args `PYTHON_IMAGE`, `UV_IMAGE`, `NODE_IMAGE` from `versions.yaml` (`repo@digest`); build context = repo root; `docker buildx build --load -f <Dockerfile> -t rootline/<name>:<tag> --build-arg ... .`; then `k3d image import -c <cluster> rootline/<name>:<tag> ...`.

- [ ] **Step 4: Run tests** → `uv run pytest tests/repo/test_up_helpers.py -v` → PASS.

- [ ] **Step 5: Bring up the cluster**

Run: `task up`. Expected: all apps `Synced/Healthy` within 20 min (the `rootline` app is Healthy with zero resources; `workload` is Healthy).

Verify pgvector (DB-001):

```bash
kubectl -n rootline-data exec rootline-pg-1 -- psql -U postgres -d rootline -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Expected: a `0.8.x` version. If it fails, build `deploy/images/postgres/Dockerfile` (`FROM ghcr.io/cloudnative-pg/postgresql:16` + `apt-get install -y postgresql-16-pgvector`), record the decision in an ADR (next free number), set `postgres-image` in `versions.yaml`, and re-run.

- [ ] **Step 6: Measure memory (S2)** — `task doctor` → `memory_requests_total` ≤ 9.5 GiB. Write `wiki/components/capacity.md`: a table of every pod's memory request from `kubectl get pods -A -o json` (component, namespace, request, limit) and the total, dated. If > 9.5 GiB, apply ARC-031 reductions in order, recording each with the new total. The workload budget (≤ 3.2 GiB, ARC-030) is checked by summing namespace `shop`; if it exceeds 3.2 GiB, set per-component requests in the render values (`components.<name>.resources.requests.memory`) to bring the sum under 3.2 GiB and re-render (this is a re-render that bumps `baseline-v2`, WKL-001).

- [ ] **Step 7: Run `task trust-ca`** and open `https://argocd.127.0.0.1.sslip.io` in the Windows browser (`/mnt/c/Windows/explorer.exe "https://argocd.127.0.0.1.sslip.io"` from WSL); log in as `admin`. Record the result in `wiki/runbooks/local-up.md`, which now documents: prerequisites, `.env.local` keys for week 1, `task up`, expected duration, URLs, admin password retrieval, `task stop/start/down`, and troubleshooting (apps stuck `Progressing` → `kubectl -n argocd get applications`, `argocd app get` via UI).

- [ ] **Step 8: Smoke registration (overview §7.7)** — create `tests/smoke/platform.yaml` with one `argocd_app` check (`expect: Synced/Healthy`) per Application enabled for `local` in `deploy/root/values.yaml`, then run `task smoke:cluster` → all PASS.

- [ ] **Step 9: Commit** `feat: add task up bring-up for the local k3d cluster` with the wiki updates and `tests/smoke/platform.yaml`.

---

### Task W1-T13: Baseline health gate, thresholds and alert rules

**Requirement IDs:** WKL-004, WKL-022, WKL-030 (metric names), WKL-031, WKL-032.
**Depends on:** W1-T12. **Branch:** `feat/w1-baseline-gate`.

**Files:**
- Create: `scripts/baseline_gate.py`, `scripts/derive_thresholds.py`, `scripts/promql.py`
- Create: `deploy/values/alert-thresholds.yaml` (generated, committed)
- Create: `deploy/charts/observability/templates/prometheusrule-workload.yaml`, `deploy/charts/observability/templates/alertmanager-config.yaml`
- Create: `deploy/charts/observability/files/metric-map.yaml` (the WKL-030 PromQL templates with names finalised per WKL-022)
- Modify: `wiki/components/telemetry.md`, `wiki/components/workload.md`
- Test: `tests/repo/test_thresholds.py`, `tests/repo/test_alert_rules.py`

**Interfaces:**
- Produces: `deploy/charts/observability/files/metric-map.yaml` with schema `{metrics: {<metric_key>: {unit: str, promql: str, jvm_only: bool, services: [str] | null}}}` — the single source of PromQL for `mcp-telemetry` live mode (W3-T06) and the Fault Lab exporter (W2-T09); `scripts.promql.PromClient(base_url)` with `query(expr, ts)`, `query_range(expr, start, end, step_s)`; `scripts.derive_thresholds.derive(samples: dict[str, list[float]]) -> dict`.

- [ ] **Step 1: Discover telemetry names (WKL-022)** — with the cluster up for ≥ 15 min, port-forward Prometheus (`kubectl -n observability port-forward svc/prometheus-operated 9090`) and record in `wiki/components/telemetry.md`:
  - span-metrics metric names and labels: `curl -s localhost:9090/api/v1/label/__name__/values | jq -r '.data[]' | grep -E 'traces_spanmetrics|traces_service_graph'`
  - label names on `traces_spanmetrics_calls_total`: `curl -s 'localhost:9090/api/v1/series?match[]=traces_spanmetrics_calls_total' | jq '.data[0]'`
  - the `service` label value for every kept component (WKL-030: `$svc`), and whether it equals the workload name
  - JVM GC metric for `ad` and `fraud-detection` (search names containing `jvm_gc`)
  - Kafka consumer lag metric for `fraud-detection` (search names containing `lag`)

- [ ] **Step 2: Write `metric-map.yaml`** with the WKL-030 keys and templates, substituting the discovered names. Example entry:

```yaml
metrics:
  request_rate:
    unit: req/s
    jvm_only: false
    services: null
    promql: sum(rate(traces_spanmetrics_calls_total{service="$svc",span_kind="SPAN_KIND_SERVER"}[1m]))
  gc_pause:
    unit: seconds per s
    jvm_only: true
    services: [ad, fraud-detection]
    promql: sum(rate(<discovered jvm gc duration sum>{service="$svc"}[1m]))
  kafka_consumer_lag:
    unit: records
    jvm_only: false
    services: [fraud-detection]
    promql: <discovered lag expression>
```

Every key of WKL-030 appears exactly once; `latency_p50/p95/p99` are three entries.

- [ ] **Step 3: Tests for threshold derivation**

```python
"""Verifies WKL-031 († thresholds)."""
from scripts.derive_thresholds import derive


def test_latency_threshold_is_max_of_1s_and_3x_p95() -> None:
    out = derive({"latency_p95:payment": [0.1] * 100, "latency_p95:checkout": [0.5] * 100,
                  "kafka_consumer_lag:fraud-detection": [10.0] * 100})
    assert out["ServiceHighLatency"]["payment"] == 1.0
    assert out["ServiceHighLatency"]["checkout"] == 1.5
    assert out["KafkaConsumerLagHigh"]["fraud-detection"] == 1000.0


def test_baseline_p95_uses_95th_percentile() -> None:
    vals = [float(i) for i in range(1, 101)]
    out = derive({"latency_p95:x": vals})
    assert out["baseline_p95"]["x"] == 95.05
```

Implementation: `baseline_p95[svc] = numpy.percentile(values, 95)` (linear interpolation, rounded to 4 decimals); `ServiceHighLatency[svc] = max(1.0, round(3 * baseline_p95, 4))`; `KafkaConsumerLagHigh[svc] = max(1000.0, 10 * percentile(lag, 95))`.

- [ ] **Step 4: `baseline_gate.py`** — `--minutes 30` (default), polls every 60 s via `PromClient`; at the end computes per kept server-side service (every kept component except `load-generator`, `frontend-proxy`, `kafka`, `valkey-cart`, `astronomy-db`, `flagd`): mean `error_ratio` over the 30 min using `avg_over_time` of the metric-map expression with a 30 m range, and `restarts` via `increase(kube_pod_container_status_restarts_total{namespace="shop"}[30m])`. Prints a table `service | error_ratio | restarts | PASS/FAIL` and exits 1 if any `error_ratio > 0.01` or restarts > 0. Also writes `data/baseline/<date>/samples.json` with 15 s range queries for `latency_p95` (all services) and `kafka_consumer_lag`, which `derive_thresholds.py --samples <file>` consumes to write `deploy/values/alert-thresholds.yaml`:

```yaml
# GENERATED by scripts/derive_thresholds.py from the WKL-004 baseline run on <date>. Do not edit.
baseline_p95: {payment: 0.0123, ...}
ServiceHighLatency: {payment: 1.0, ...}
KafkaConsumerLagHigh: {fraud-detection: 1000.0}
```

- [ ] **Step 5: Run the gate (WKL-004)** — `uv run python scripts/baseline_gate.py --minutes 30`. On FAIL, follow WKL-004 (re-enable the missing dependency in `deploy/upstream/otel-demo/values.yaml` or disable the load-generator task via its documented env var), re-render (bump `baseline-v2`), re-run until PASS. Record the outcome table in `wiki/components/workload.md`.

- [ ] **Step 6: Alert rules template** — `prometheusrule-workload.yaml` renders `PrometheusRule rootline-workload` in `observability` from `metric-map.yaml` and `alert-thresholds.yaml` (copied into `deploy/charts/observability/files/` by `derive_thresholds.py`). One rule group `rootline-workload`; per-service rules are generated with one rule per (alert, service) for the per-service alerts and one rule for the cluster-wide kube-state-metrics alerts. Every rule has labels `rootline: "true"`, `namespace: shop`, `service: <svc>` (for kube-state-metrics rules: `service` is derived with `label_replace(..., "service", "$1", "pod", "(.*)-[a-z0-9]+-[a-z0-9]+")` for Deployment pods and `"$1", "pod", "(.*)-[0-9]+"` for StatefulSets), `severity`, and annotation `summary`. Expressions, `for` and severities exactly as the WKL-031 table. `HighCPU`/`HighMemory` use `kube_pod_container_resource_limits{resource="cpu|memory"}`; services without limits are excluded by the `and` on the limit series.

Test (`tests/repo/test_alert_rules.py`): render the chart, load the `PrometheusRule`, assert there is exactly one rule named `ServiceHighErrorRate` per kept server-side service with `for: 1m`, `labels.severity == "critical"`, `labels.rootline == "true"`, and that the expression text contains `> 0.05` and `> 0.1`; assert `PodCrashLooping` has `for: 0m`; run `promtool check rules` on the extracted rule file when `promtool` is on PATH (skip otherwise).

- [ ] **Step 7: Alertmanager config** — `alertmanager-config.yaml` renders an `AlertmanagerConfig` (or the chart's `alertmanager.config` values; choose `AlertmanagerConfig` CRD with `alertmanagerConfigMatcherStrategy: None` set in values) with route `group_by: [alertname, service]`, `group_wait: 30s`, `group_interval: 2m`, `repeat_interval: 1h`, single receiver `rootline-api` webhook `http://api.rootline.svc.cluster.local/hooks/alertmanager`, `sendResolved: true`, `httpConfig.authorization.credentials: {name: alertmanager-webhook, key: token}`. The Secret `observability/alertmanager-webhook` comes from an ExternalSecret using generator `password-48` (created now in `platform-config`; the `rootline` copy comes in W4-T13 via the same generated value — use a `PushSecret`-free approach: the ExternalSecret in `observability` generates it, and an ExternalSecret in `rootline` reads it through a ClusterSecretStore `observability-reader` (Kubernetes provider, remote namespace `observability`, Role limited to secret `alertmanager-webhook`)).

- [ ] **Step 8: Verify** — sync, then `kubectl -n observability get prometheusrules rootline-workload -o yaml | grep -c "alert:"` equals the expected rule count printed by the test; Prometheus UI `/alerts` shows the rules in state `inactive`.

- [ ] **Step 9: Commit** `feat(deploy): add workload alert rules, thresholds and baseline gate` with wiki updates.

---

### Task W1-T14: CI workflow `ci.yml` and repository ruleset

**Requirement IDs:** CI-001 (`ci.yml`), CI-002, GEN-020, WIK-020, O-3.
**Depends on:** W1-T01 … W1-T13 merged or on the same branch. **Branch:** `feat/w1-ci`.

**Files:**
- Create: `.github/workflows/ci.yml`, `scripts/ci_changed_files.py`
- Modify: `wiki/runbooks/github-apps.md` (section `## Rulesets`)

- [ ] **Step 1: Write `ci.yml`**

```yaml
name: ci
on:
  pull_request: {branches: [develop, main]}
  push: {branches: [develop, main]}
concurrency: {group: "ci-${{ github.ref }}", cancel-in-progress: true}
permissions: {contents: read, pull-requests: read}

jobs:
  python:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: astral-sh/setup-uv@v6
        with: {version: "${{ env.V_UV }}"}
      - run: uv python install ${{ env.V_PYTHON }}
      - run: uv sync --all-packages --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy --strict services libs eval/runner
      - run: uv run pytest -m "not integration and not k8s" --cov --cov-report=xml
      - run: uv run pytest -m integration -v
  console:
    runs-on: ubuntu-24.04
    if: ${{ hashFiles('apps/console/package.json') != '' }}
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: actions/setup-node@v4
        with: {node-version: "${{ env.V_NODE }}", cache: npm, cache-dependency-path: apps/console/package-lock.json}
      - run: npm --prefix apps/console ci
      - run: npm --prefix apps/console run lint
      - run: npm --prefix apps/console run typecheck
      - run: npm --prefix apps/console run test -- --run
  policy:
    runs-on: ubuntu-24.04
    if: ${{ hashFiles('policies/opa/**/*.rego', 'policies/kyverno/**/*.yaml') != '' }}
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: open-policy-agent/setup-opa@v2
        with: {version: "${{ env.V_OPA }}"}
      - run: opa fmt --diff --fail policies/opa
      - run: opa test policies/opa -v
      - run: |
          curl -sSL -o kyverno.tgz "https://github.com/kyverno/kyverno/releases/download/v${V_KYVERNO_CLI}/kyverno-cli_v${V_KYVERNO_CLI}_linux_x86_64.tar.gz"
          tar -xzf kyverno.tgz kyverno && ./kyverno test policies/kyverno
  infra:
    runs-on: ubuntu-24.04
    if: ${{ hashFiles('infra/terraform/**/*.tf') != '' }}
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: hashicorp/setup-terraform@v3
        with: {terraform_version: "${{ env.V_TERRAFORM }}"}
      - run: terraform fmt -check -recursive infra/terraform
      - run: for d in infra/terraform/persistent infra/terraform/cluster; do terraform -chdir=$d init -backend=false && terraform -chdir=$d validate; done
      - uses: terraform-linters/setup-tflint@v4
        with: {tflint_version: "v${{ env.V_TFLINT }}"}
      - run: tflint --recursive --chdir infra/terraform
      - uses: aquasecurity/trivy-action@0.33.1
        with: {scan-type: config, scan-ref: infra/terraform, exit-code: "1", severity: "CRITICAL,HIGH"}
  manifests:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: astral-sh/setup-uv@v6
      - uses: azure/setup-helm@v4
      - run: for c in deploy/root deploy/charts/*; do helm dependency build "$c" || true; helm lint "$c"; done
      - run: |
          curl -sSL "https://github.com/yannh/kubeconform/releases/download/v${V_KUBECONFORM}/kubeconform-linux-amd64.tar.gz" | tar -xz kubeconform
          uv run python scripts/render_manifests.py | ./kubeconform -strict -summary -ignore-missing-schemas \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'
  contracts:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - uses: azure/setup-helm@v4
      - run: uv sync --all-packages --frozen
      - run: uv run python scripts/render_versions.py --check
      - run: uv run pytest tests/repo/test_workload_render.py -v
      - if: ${{ hashFiles('services/api/openapi.json') != '' }}
        run: uv run python scripts/check_contracts.py
  wiki:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - uses: astral-sh/setup-uv@v6
      - run: uv run python scripts/wiki_lint.py
      - if: github.event_name == 'pull_request'
        env: {GH_TOKEN: "${{ github.token }}"}
        run: |
          git diff --name-only "origin/${{ github.base_ref }}...HEAD" > changed.txt
          gh pr view ${{ github.event.pull_request.number }} --json body --jq .body > body.txt
          uv run python scripts/wiki_lint.py --changed-files changed.txt --pr-body body.txt
  security:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - uses: gitleaks/gitleaks-action@v2
        env: {GITHUB_TOKEN: "${{ github.token }}"}
      - uses: astral-sh/setup-uv@v6
      - run: uv export --all-packages --frozen --no-hashes > requirements.txt && uvx pip-audit -r requirements.txt
      - if: ${{ hashFiles('apps/console/package-lock.json') != '' }}
        run: npm --prefix apps/console audit --audit-level=high
  required:
    if: always()
    needs: [python, console, policy, infra, manifests, contracts, wiki, security]
    runs-on: ubuntu-24.04
    steps:
      - run: |
          echo '${{ toJSON(needs) }}' > needs.json
          python3 -c "import json,sys;n=json.load(open('needs.json'));bad=[k for k,v in n.items() if v['result'] not in ('success','skipped')];print('failed:',bad);sys.exit(1 if bad else 0)"
```

`uv run ruff format --check .` stays exactly as written. Do not add a `uv run ruff format .` step and do not reformat any file in this task: Markdown files are excluded from ruff by `extend-exclude = ["*.md"]` in the root `pyproject.toml`, and `tests/repo/test_layout.py` is already ruff-formatted (both done by W1-T16 Step 0, PG-19). W1-T14 runs in the parallel stage W1-P3 and may change only its `owns` paths (overview §7.4); a repository-wide reformat would change files owned by W1-T09, W1-T10 and W1-T11 and fail gate check G1. If the `python` job's format step fails on a file, the failure belongs to the task that last changed that file (overview §7.8).

`V_*` variables come from `.github/versions.env` (W1-T02). Third-party action versions above are the major versions current on the planning date; on the pin date use the latest major of each and pin it by commit SHA (`uses: owner/action@<40-hex sha> # vX.Y.Z`), recording the SHAs in `wiki/versions.md`. `scripts/check_contracts.py` is created in W4-T06.

- [ ] **Step 2: Push and verify** — open the PR; all jobs green or skipped; `required` green.

- [ ] **Step 3 [OWNER] (O-3): Create the rulesets on `rootline`** (GEN-020). Document the exact clicks in `wiki/runbooks/github-apps.md` § Rulesets, or run with confirmation:

```bash
gh api -X POST repos/arkhash0309/rootline/rulesets --input .github/rulesets/main.json
gh api -X POST repos/arkhash0309/rootline/rulesets --input .github/rulesets/develop.json
```

`.github/rulesets/main.json`: `{"name":"protect-main","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"deletion"},{"type":"non_fast_forward"},{"type":"required_linear_history"},{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,"required_status_checks":[{"context":"ci / required"}]}}],"bypass_actors":[{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}]}` (actor 5 = repository admin role). `develop.json`: same without `required_linear_history` and without `bypass_actors`. Note: `required_linear_history` on `main` conflicts with the GEN-021 merge-commit release; resolve by **omitting** `required_linear_history` from `main.json` and recording the conflict in spec §26 and ADR 0025 (GEN-021 wins because it is the more specific rule).

- [ ] **Step 4: Commit** `ci: add ci.yml quality gate and branch rulesets`.

---

### Task W1-T15: Week 1 acceptance and release

**Requirement IDs:** MS-001, MS-002, S2, S9 (partial).
**Depends on:** all W1 tasks.

- [ ] **Step 1: Run the acceptance checks and capture evidence**

| Check | Command | Expected |
|---|---|---|
| Cluster healthy | `task up` (on an existing cluster it is idempotent) | all apps `Synced/Healthy` |
| Doctor | `task doctor` | no `FAIL`; `memory_requests_total ≤ 9.5` |
| Baseline gate | `uv run python scripts/baseline_gate.py --minutes 30` | all PASS |
| Wiki | `task wiki:lint` | exit 0 |
| CI | `gh run list --branch develop --workflow ci.yml -L 1` | `completed success` |
| Tests | `task test` | all pass |

- [ ] **Step 2: Update the wiki** — `status.md` (milestone Week 2 — Fault Lab; Done lists every W1 task with PR numbers), `log.md`, `cost-ledger.md` (week 1 row, USD 0).

- [ ] **Step 3: Release PR** — `gh pr create --base main --head develop --title "release: milestone 1"` with a body checklist of the table above, each item linked to its evidence (CI run URL, doctor output pasted in a `<details>` block, baseline gate table). The owner merges it with a merge commit.
