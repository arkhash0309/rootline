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
- Lint-clean code blocks (PG-21, ADR 0040, amended 2026-11-27): these blocks were changed so that the copied file, after `uv run ruff format`, passes `uv run ruff check` with the root `[tool.ruff]` settings and no finding: W1-T02 Step 1 (`import subprocess` and `import sys` on two lines, no `import pytest`, import list `CONSTRAINTS, load_versions, validate, version_of`) and Step 4 (`sys.path.insert`), W1-T03 Step 1 (no unused `import subprocess`; `[*files, "index.md", "status.md"]`) and Step 3 (`git` through `scripts.proc.run`, `sys.path.insert`), W1-T06 Step 2 (`scripts/proc.py` final text with `# noqa: S603 - …`) and Step 3 (`sys.path.insert`; the `repo-location` detail built from a `location` variable so no line exceeds 110 characters), W1-T07 Step 3 (`health.py`: `except Exception:` with a justification comment instead of `# noqa: BLE001`), W1-T09 Step 4 (`sys.path.insert`), W1-T10 Step 1 and W1-T11 Step 1 (`helm` through `scripts.proc.run`). Verified on 2026-11-27 with ruff `0.17.6`: each of these ten blocks, written to its target path next to a copy of the root `pyproject.toml`, gave `All checks passed!` from `ruff check` after `ruff format` (ADR 0040 item 1). The only lint suppression allowed in any file is `# noqa: S603 - <justification>` on the line ruff reports (overview Global Constraints "Formatting").


## Execution schedule

Mirrors `2026-11-26-rootline-schedule.yaml` (week 1); `uv run python scripts/swarm_schedule.py table --week 1` must print exactly this table. Parallel stages run in separate worktrees (at most 3 implementers at once), then pass the integration gate (overview §7.6–§7.7) before one squash-merged PR reaches `develop`. Owned paths per task are listed in the YAML only. Deferred steps (overview §7.3) run at the start of the named sequential stage.

| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |
|---|---|---|---|---|
| W1-S1 | sequential | — | W1-T01 (`feat/w1-repo-skeleton`) | — |
| W1-S2 | sequential | W1-S1 | W1-T16 (`feat/w1-swarm-tooling`); W1-T08 (`docs/w1-env-repo`) | — |
| W1-P1 | parallel | W1-S2 | W1-T02 (`feat/w1-versions`); W1-T03+W1-T04 (`feat/w1-wiki`) | W1-T02 steps 8 → W1-S3 |
| W1-P2 | parallel | W1-P1 | W1-T05 (`feat/w1-wiki-skill`); W1-T06 (`feat/w1-taskfile`); W1-T07 (`feat/w1-py-common`) | W1-T05 steps 4 → W1-S3; W1-T05 pre-dispatch steps 1 (coordinator) |
| W1-P3 | parallel | W1-P2 | W1-T09 (`feat/w1-workload-render`); W1-T11 (`feat/w1-observability-postgres`); W1-T10 (`feat/w1-gitops-root`); W1-T14 (`feat/w1-ci`) | W1-T09 steps 6, 7 → W1-S3; W1-T14 steps 2, 3 → W1-S3 |
| W1-S3 | sequential | W1-P3 | W1-T12 (`feat/w1-task-up`); W1-T13 (`feat/w1-baseline-gate`); W1-T15 (no branch) | — |

**W1-P1 integration steps (PG-22, ADR 0041 decisions 1 and 2).** These steps run in this order, in addition to overview §7.5 and §7.6:

1. The coordinator squash-merges the planner PR of branch `docs/w1-t02-gaps` into `develop`. That PR touches only `docs/superpowers/plans/`, `docs/superpowers/specs/2026-11-25-rootline-design.md`, `wiki/adr/0041-w1-t02-version-gaps.md` and `wiki/versions.md` (the three-line stub of W1-T02 "Files").
2. The coordinator records the resulting `origin/develop` commit as the W1-P1 stage base in `.swarm/stages/W1-P1.json`.
3. After the `docs/w1-t02-gaps` PR merges to develop, the W1-T02 implementer rebases `feat/w1-versions` onto the new `origin/develop` (`git fetch origin && git rebase origin/develop`; the rebase is clean because the PR touches only plans, spec, ADR and `wiki/versions.md`, and the `wiki/versions.md` stub on `develop` is byte-identical to the one on `feat/w1-versions`), then pushes with `git push --force-with-lease origin feat/w1-versions` (task branches are unprotected, overview §7.6). Only then is `uv run python scripts/check_ownership.py --task W1-T02 --base origin/develop --branch HEAD` run in the W1-T02 worktree; it reads the schedule YAML from that checkout, which now lists `wiki/versions.md` in W1-T02 `owns`. Expected: no output, exit 0. If the rebase stops on a conflict, the implementer runs `git rebase --abort` and reports `STATUS: BLOCKED` with the conflicting paths; the planner then designs the resolution.
4. The coordinator dispatches W1-T03 (branch `feat/w1-wiki`, base = the stage base of step 2), creates `integration/w1-p1` from the same stage base, and continues with overview §7.6.

**W1-P3 integration steps (PG-27, ADR 0046 decisions T1, T8, T11 and O3).** The W1-P3 task order is W1-T09, W1-T11, W1-T10, W1-T14 (changed on 2026-11-27 so that W1-T11 is merged before W1-T10). These steps run in this order, in addition to overview §7.5 and §7.6:

1. Fix rounds (overview §7.5). The W1-T11 implementer applies, on `feat/w1-observability-postgres`, the ADR 0046 items O1 to O5, T1 step 1 and T11 step 1 (W1-T11 amendment note). The W1-T10 implementer applies, on `feat/w1-gitops-root`, the items T2 (except the removal of `| default dict` and the overrides), T3, T4, T5, T7, T9, T10 and O3 item 1 (W1-T10 amendment note). Each task is re-reviewed until `APPROVE`.
2. The coordinator creates `integration/w1-p3` from the W1-P3 stage base recorded in `.swarm/stages/W1-P3.json` and merges, with overview §7.6 step 2, `feat/w1-workload-render` (W1-T09) and then `feat/w1-observability-postgres` (W1-T11).
3. Before merging W1-T10, the coordinator dispatches the W1-T10 implementer with `mode: resolve-conflict` and this step as its task. In the W1-T10 worktree: `git fetch origin && git rebase origin/integration/w1-p3`. A conflict in `deploy/root/files/versions.yaml` or `.github/versions.env` is resolved by taking either side and running `uv run python scripts/render_versions.py` (overview §7.4); any other conflict makes the implementer run `git rebase --abort` and report `STATUS: BLOCKED` with the conflicting paths, and the planner designs the resolution. Then the implementer makes the ADR 0046 T1 step 3 changes (remove `repo` and `chartVersion` from `apps.prometheus-crds`; the T2 `upstream` template text with `required`), the T8 item 3 change (remove `--allow-missing`) and the T11 item 2 change (`copyCa.image` removed; `ca-configmap.yaml` reads `files/versions.yaml`), runs `uv run python scripts/render_versions.py` (it writes `deploy/charts/platform-config/files/versions.yaml`), and runs, each with exit 0: `uv run python scripts/render_versions.py --check`; `uv run pytest tests/repo/test_root_chart.py tests/repo/test_versions.py tests/repo/test_observability_values.py -v`; `uv run python scripts/render_manifests.py | kubeconform -strict -summary -ignore-missing-schemas -schema-location default -schema-location "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"` (0 invalid); `uv run python scripts/check_ownership.py --task W1-T10 --base origin/integration/w1-p3 --branch HEAD`. It commits `fix(deploy): read prometheus-operator-crds and kubectl-image from generated versions (ADR 0046)` with the implementer trailer and runs `git push --force-with-lease origin feat/w1-gitops-root`.
4. The reviewer re-reviews only the rebase and the new commit: `git range-diff <W1-P3 stage base>..<approved W1-T10 sha> origin/integration/w1-p3..origin/feat/w1-gitops-root` (the approved commits must appear unchanged apart from conflict resolutions) and `git show origin/feat/w1-gitops-root` (the new commit). On `APPROVE` the coordinator merges `feat/w1-gitops-root`, then `feat/w1-ci` (W1-T14), and continues with overview §7.6 step 3.
5. **[CONFIRM]** Before the W1-P3 integration PR is merged into `develop` (overview §7.6 step 5), the coordinator asks the owner to confirm ADR 0046 O3: namespace `observability` moves from PSS `enforce: baseline` to `enforce: privileged` (with `warn` and `audit` at `baseline`) so the collector DaemonSet `otel-collector-agent` can mount `/var/log/pods` read-only, and Kyverno restores the `baseline` checks for every other pod there from W3-T12. Options for the owner: (a) confirm (recommended); (b) drop the `file_log` receiver from WKL-020 and keep `baseline`; (c) move the collector to its own `privileged` namespace. On (a) the coordinator records the confirmation in the integration PR body and merges. On (b) or (c) the coordinator does not merge and dispatches the planner to re-plan W1-T10 and W1-T11.

---

### Task W1-T01: Repository skeleton and uv workspace

**Requirement IDs:** GEN-001, GEN-002, GEN-003, GEN-022, GEN-023, WIK-031, PG-8.
**Depends on:** nothing. **Branch:** `feat/w1-repo-skeleton`.

> **Amended 2026-11-26 after W1-T01 was merged (`develop` at `4898699`), per PG-18, PG-19 and PG-20 (overview §5; ADRs 0037, 0038, 0039).** Four code blocks of this task changed after the merge: (1) the `tests/repo/test_layout.py` block in Step 1 is now the `ruff format` output of the original block and its `ALLOWED_TOP_LEVEL` set gains `".hypothesis"`, `".coverage"`, `"coverage.xml"`, `"htmlcov"` and `".swarm"`; (2) the `[tool.ruff]` table in Step 3 gains `extend-exclude = ["*.md"]`; (3) the Step 9 trailer is the implementer trailer of overview §7.1; (4) the trailer bullet of the Step 7 block is the owner-approved per-role bullet (PG-20, ADR 0039), and its Conventional Commits bullet lists `revert:` after `perf:` (owner decision 2026-11-26, PG-20, ADR 0039). The files committed in `4898699` still have the original content. Item (4) is already applied to `CLAUDE.md` and `AGENTS.md` by branch `docs/w1-plan-gaps`, so W1-T16 Step 0 does not touch those two files. **W1-T16 Step 0** brings `tests/repo/test_layout.py` and `pyproject.toml` in line with these blocks in one commit; W1-T01 is not re-run. The committed history is not rewritten.

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

- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, `build:`, `perf:`, `revert:`, with optional scope = component directory name, e.g. `feat(agent): add verify node`.
- Commits end with the trailer for your role in `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §7.1, "Commit attribution trailers" (implementer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, planner `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, coordinator `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`).
```

This block is identical to the "Commit rules (GEN-022)" section of `CLAUDE.md` and `AGENTS.md` on `develop`. Its trailer bullet was approved by the owner on 2026-11-26 (overview §5 PG-20, ADR 0039) and committed on branch `docs/w1-plan-gaps`; the files in `4898699` still carry the earlier bullet "Commits authored by AI agents end with the attribution trailer in use in the session, currently: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`", and that commit is not rewritten. The bullet repeats the table in overview §7.1 "Commit attribution trailers (GEN-022, PG-20)"; if the two ever differ, the §7.1 table decides.

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

**Requirement IDs:** PG-16 (overview §7), PG-18, PG-19, PG-20, PG-21, GEN-001, GEN-022, CI-001, GEN-041, WIK-020, TST-002, TST-010.
**Depends on:** W1-T01. Runs in stage W1-S2, before every parallel stage (schedule `W1-S2`). **Branch:** `feat/w1-swarm-tooling`.

> **Amended 2026-11-27 after the W1-T16 review, per PG-21 (overview §5; ADR 0040).** The "Files", "Interfaces", Step 1 test descriptions, Steps 2, 3, 4, 5 and 8 and the dev-group paragraph after Step 9 now state: the `# noqa: S603 - <justification>` rule and the `S607`/`BLE001` rules (ADR 0040 item 1), the required `namespace` of `exec` smoke checks (item 2), the `next` output strings and exit codes (item 3), the wave-table comparison in `validate` (item 4), `--no-renames -z` and exit code 2 in `check_ownership.py` (item 5), root anchoring in `matches` (item 6), the `--stage` mode used by G1 on integration branches (item 7), and the gate's check names, `env --chdir` runner, 3600 s timeout, `setup worktree` and `setup uv-sync` results, exit code 2 for an unknown stage or an unresolvable ref, and G10 `results` comparison (item 8). The fix branch `fix/w1-t16-adr-0040` must be merged into develop before stage W1-P1 is dispatched, because the merged `scripts/proc.py` line 21 has a bare `# noqa: S603` that the W1-T06 Step 2 check rejects.

**Files:**
- Modify (Step 0, its own commit): `tests/repo/test_layout.py` (replace with the W1-T01 Step 1 block), `pyproject.toml` (add `extend-exclude = ["*.md"]` to `[tool.ruff]`)
- Create: `scripts/__init__.py` (empty, size 0; makes `scripts.*` importable in tests and in scripts that insert the repository root into `sys.path`, ADR 0040 item 9), `scripts/proc.py` (moved here from W1-T06), `scripts/swarm_schedule.py`, `scripts/check_ownership.py`, `scripts/integration_gate.py`, `scripts/cluster_smoke.py`, `scripts/swarm_lib.py`
- Create: `tests/registry/README.md`, `tests/smoke/README.md`, `tests/registry/schema.json`, `tests/smoke/schema.json`
- Modify (Steps 2 and 8, in the Step 9 commit): `pyproject.toml` — add `pythonpath = ["."]` as the first line of `[tool.pytest.ini_options]`; append `"pathspec>=0", "jsonschema>=0", "types-jsonschema"` to the root `dev` dependency group (paragraph after Step 9); `uv.lock` (regenerated by `uv lock`)
- Modify: `.gitattributes` (add `wiki/log.md merge=union`), `.gitignore` (add `.swarm/`, `.hypothesis/`, `coverage.xml`)
- Test: `tests/repo/test_swarm_schedule.py`, `tests/repo/test_check_ownership.py`, `tests/repo/test_integration_gate.py`, `tests/repo/test_cluster_smoke.py`

W1-T16 is in a sequential stage, so the schedule gives it no `owns` list and `scripts/check_ownership.py` passes it for every path (overview §7.4, W1-T16 Step 3). Changing `tests/repo/test_layout.py`, a W1-T01 file, is therefore allowed here and needs no schedule change.

**Interfaces:**
- `scripts.proc.run(cmd, *, check=True, capture=True, env=None, timeout=600, input_text=None) -> CompletedProcess[str]` (exact code in W1-T06 step 2, including its `# noqa: S603 - …` comment, ADR 0040 item 1; W1-T06 now imports it instead of creating it). It has no `cwd` parameter; callers that need another directory use `git -C <dir>` or the gate's `env --chdir` runner (below).
- `scripts.swarm_lib.load_schedule(path=REPO/"docs/superpowers/plans/2026-11-26-rootline-schedule.yaml") -> Schedule`; dataclasses `Schedule(version, max_parallel_implementers, always_allowed: list[str], weeks: list[Week])`, `Week(week, stages: list[Stage])`, `Stage(id, mode, after, tasks: list[TaskEntry])`, `TaskEntry(id, branch, combined_with, owns, excludes, pre_steps, deferred_steps, deferred_to)`; `matches(path: str, globs: list[str]) -> bool` (gitignore-style via `pathspec.GitIgnoreSpec`, but a pattern without `/` is anchored at the repository root, so `pyproject.toml` matches only the root file and `**/pyproject.toml` matches every depth — ADR 0040 item 6; an empty `globs` list matches nothing; add `pathspec` to `versions.yaml` and the root dev group); `is_owned(task: TaskEntry, path: str) -> bool` = `matches(path, task.owns) and not matches(path, task.excludes)`.
- CLI `uv run python scripts/swarm_schedule.py validate | next --week N | done <stage> | show <stage> | table --week N`; progress file `.swarm/progress.json` = `{"done": [stage ids], "stage_bases": {stage: sha}}` (a missing file reads as `{"done": [], "stage_bases": {}}`). Output and exit codes:

| Subcommand | Prints (stdout, exact) | Exit |
|---|---|---|
| `validate`, no error | `schedule OK: <weeks> weeks, <stages> stages, <tasks> tasks` (tasks count `combined_with` entries) | 0 |
| `validate`, errors | one line per error: every `validate_schedule` rule of Step 1, then the wave-table comparison (ADR 0040 item 4): `W<N>: expected exactly one wave file matching *-w<N>-*.md`, `W<N>: <file> has no execution schedule table`, `W<N>: execution schedule table in <file> differs from the YAML (print it with: uv run python scripts/swarm_schedule.py table --week <N>)`. All eight wave files must match the rendered table character for character | 1 |
| `next --week N`, a stage is runnable | the ID of the first stage of week N, in schedule order, that is not in `done` and whose `after` stages are all in `done` | 0 |
| `next --week N`, every stage of week N in `done` | `week N complete` (for example `week 1 complete`) | 0 |
| `next --week N`, stages remain but none is runnable | `no runnable stage in week N; not done: <ids>` (`<ids>` = not-done stage IDs of week N in schedule order, joined by `, `) | 1 |
| `next --week N` or `table --week N`, week not in the schedule | `unknown week: N` | 1 |
| `done <stage>` | `done: <stage>` (appends to `done` once; a repeat changes nothing) | 0 |
| `done <stage>` or `show <stage>`, unknown stage | `unknown stage: <stage>` | 1 |
| `show <stage>` | `<id> (<mode>) after: <ids or ->`, then per task `- <id>[+<combined id>…] branch: <branch or none>` and indented lines `owns:`, `excludes:`, `pre_steps:`, `deferred_steps: <steps> -> <deferred_to>` (`-` for an empty value) | 0 |
| `table --week N` | the Markdown "Execution schedule" table of week N | 0 |

- CLI `uv run python scripts/check_ownership.py (--task <id> | --stage <id>) --base <sha> [--branch <ref>]` (exactly one of `--task`, `--stage`; `--branch` default `HEAD`). Changed files = `git diff --name-only --diff-filter=ACMRD --no-renames -z <base>...<branch>` split on NUL; with `--no-renames` a rename is a deletion of the old path plus an addition of the new path and both paths are checked (ADR 0040 item 5). A path passes with `--task` when `is_owned(task, path)`, with `--stage` when `is_owned(t, path)` for at least one task `t` of the stage (ADR 0040 item 7); in both modes it also passes when `matches(path, always_allowed)` and the overview §7.4 special rule for that path holds. A task or stage without `owns` (sequential) passes every path. Exit 0 = every path passes; exit 1 = one stdout line per offending path, `ownership: <path> not owned by <task id>` (`--task`) or `ownership: <path> not owned by any task of <stage id>` (`--stage`); exit 2 = unknown task or stage (stderr `unknown task: <id>` / `unknown stage: <id>`) or a `git` command exited non-zero (stderr `git <args> failed: <git stderr>`).
- CLI `uv run python scripts/integration_gate.py --stage <id> [--branch <ref>] [--base origin/develop] [--pr-body <file>] [--report-only]` → checks G1–G11 of overview §7.7 (G12 is `cluster_smoke.py`), report `.swarm/gates/<stage>.json`, exit 1 on any `fail` (exit 0 with `--report-only`), exit 2 for an unknown stage or a ref that `git rev-parse --verify <ref>^{commit}` cannot resolve. `--branch` default `integration/<stage id lowercase>`. Gate behaviour fixed by ADR 0040 item 8:

| Topic | Behaviour |
|---|---|
| Check names | each report entry's `name` is `G<n> <label>`, in this run order: `G1 ownership`, `G2 uv-lock`, `G2 npm-ci`, `G3 versions`, `G3 contracts`, `G3 prompt-hashes`, `G3 scenarios`, `G4 alembic-heads`, `G4 migrations-test`, `G5 ruff`, `G5 ruff-format`, `G5 mypy`, `G5 eslint`, `G5 tsc`, `G5 helm-lint`, `G5 kubeconform`, `G5 terraform-fmt`, `G5 terraform-validate`, `G5 tflint`, `G5 opa-fmt`, `G6 pytest`, `G6 console`, `G6 opa`, `G6 kyverno`, `G7 coverage`, `G8 registry`, `G9 test-count`, `G10 replay`, `G11 wiki`. Skip reasons name the check, for example `G6 console: apps/console/package.json missing` is the entry `{name: "G6 console", status: "skip", reason: "apps/console/package.json missing"}`. A check function that raises is recorded under its own name with `fail` and reason `internal error: <repr of the exception>`, and the gate continues |
| G1 | parallel stage: `uv run python scripts/check_ownership.py --stage <stage id> --base <base sha> --branch <head sha>` in the coordinator's repository; `pass` on exit 0, `fail` with reason `exit <code>` on exit 1 or 2. Sequential stage: `skip`, reason `stage <id> is sequential` |
| Command runner | the default runner runs `["env", "--chdir", "<worktree>", *cmd]` through `scripts.proc.run(…, check=False, timeout=3600)`, because `proc.run` has no `cwd` |
| Timeout | 3600 s per command; on `subprocess.TimeoutExpired` the runner returns exit `124` with stderr `timeout after 3600 s: <command joined by spaces>`, and the check is `fail`, reason `exit 124` |
| Setup | after `git worktree add --detach` of `.swarm/worktrees/<stage>` (head) and `.swarm/worktrees/<stage>-base` (base), the gate runs `uv sync --all-packages --frozen` in the head worktree. Non-zero exit → `checks` = `[{name: "setup uv-sync", status: "fail", reason: "exit <code>", duration_s: 0.0, output_tail: <last 40 lines>}]`, no G-check runs, both worktrees are removed, the report is written, exit 1 (0 with `--report-only`) |
| Setup worktree | `git worktree add --detach <path> <sha>` runs for the head worktree, then the base worktree. Non-zero exit of either → `checks` = `[{name: "setup worktree", status: "fail", reason: "git worktree add <path> failed: <git stderr>", duration_s: 0.0, output_tail: ""}]`, `uv sync` and the G-checks do not run, any worktree already created is removed, the report is written, exit 1 (0 with `--report-only`) |
| Exit 2 | unknown stage (stderr `unknown stage: <id>`) or a `--base`/`--branch` ref that `git rev-parse --verify <ref>^{commit}` cannot resolve (stderr `cannot resolve base <ref>` / `cannot resolve branch <ref>`): exit 2 before any worktree is created and without writing a report; `--report-only` does not change it |
| G10 | `uv run rootline-eval baseline --split smoke --write-regression <temporary file>` in the head worktree; compares only the parsed value of the top-level key `results` of the temporary file with that of the committed `eval/baselines/baseline-smoke.json` (`git_sha` and other keys are ignored). Equal → `pass`; different → `fail` unless the PR body has `baseline-change: <reason>` and the committed file differs from the base's file |

- CLI `uv run python scripts/cluster_smoke.py [--context k3d-rootline] [--timeout 1200]` → G12. `exec` checks require `namespace` (ADR 0040 item 2).

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

`tests/repo/test_check_ownership.py` (uses a temporary git repo created with `git init` in `tmp_path`, a schedule fixture and two commits; every `git` call in the test goes through `scripts.proc.run(["git", "-C", str(root), …])`, never `subprocess` directly, ADR 0040 item 1): a change inside `owns` passes; a change in `excludes` fails; `wiki/log.md` passes (always-allowed); a non-empty `__init__.py` outside `owns` fails; an empty one passes; a `pyproject.toml` change that touches only `dependencies` passes, one that changes `[project] name` fails (parse both versions with `tomllib` and compare everything except `project.dependencies`, `project.optional-dependencies` and `dependency-groups`); sequential tasks always pass; renaming an owned file to a path outside `owns` fails for the new path, and renaming a file the task does not own into `owns` fails for the old path (`--no-renames`); with `--stage`, a path owned by the second task of a two-task parallel stage passes and a path owned by neither fails with `ownership: <path> not owned by any task of <stage>`; an unknown task and an unknown base ref each exit 2.

`tests/repo/test_integration_gate.py`: with every external command replaced by a fake runner (`integration_gate.run_checks(stage, branch, base, runner=fake)`), assert the checks run in order G1…G11, that a missing tool or input yields `skip` with a reason (for example `G6 console: apps/console/package.json missing`), that one failing check makes the exit code 1, that `--report-only` exits 0, that the JSON report has the overview §7.7 shape, that G8 fails when a registry file present at the base is missing on the branch unless the PR body contains `registry-removal: <id> <reason>`, that G9 fails when the collected test count drops without `test-removal:`, and that G10 is `skip` while `eval/baselines/baseline-smoke.json` does not exist.

`tests/repo/test_cluster_smoke.py`: parses `tests/smoke/*.yaml` fixtures; an `http` check builds the command `kubectl --context <ctx> -n <ns> port-forward svc/<service> <local>:<port>` and requests `http://127.0.0.1:<local><path>`; an `exec` check builds `kubectl --context <ctx> -n <namespace> get pods -l <pod_selector> -o jsonpath={.items[0].metadata.name}` and then `kubectl --context <ctx> -n <namespace> exec <pod> -c <container> -- <command…>`; an `argocd_app` check builds the expected `kubectl` command (fake runner); invalid smoke files are rejected against `tests/smoke/schema.json`, including an `exec` check without `namespace` (ADR 0040 item 2).

`tests/repo/test_swarm_schedule.py` also covers (ADR 0040 items 3, 4, 6): `next --week N` prints the first runnable stage ID and exits 0, prints `week N complete` and exits 0 when every stage is done, prints `no runnable stage in week N; not done: <ids>` and exits 1 when stages remain but none is runnable, and prints `unknown week: N` and exits 1 for an unknown week (progress file in `tmp_path`); `validate` reports `W<N>: execution schedule table in <file> differs from the YAML (…)` for a wave file whose table differs; `matches("libs/x/pyproject.toml", ["pyproject.toml"])` is false and `matches("pyproject.toml", ["pyproject.toml"])` is true.

Run: `uv run pytest tests/repo/test_swarm_schedule.py tests/repo/test_check_ownership.py tests/repo/test_integration_gate.py tests/repo/test_cluster_smoke.py -v` → FAIL (modules missing).

- [ ] **Step 2: Implement `scripts/proc.py`** exactly as given in W1-T06 step 2, and `scripts/swarm_lib.py` + `scripts/swarm_schedule.py`. `next --week N` prints the first stage of week N whose `after` stages are all in `progress.done` and which is not itself done, with the exact outputs and exit codes of the "Interfaces" table above (`week N complete`, `no runnable stage in week N; not done: <ids>`, `unknown week: N`); `done <stage>` appends to `progress.done`; `show <stage>` prints the stage's tasks with branch, owns, pre/deferred steps; `table --week N` prints the Markdown "Execution schedule" table used in the wave files (columns `Stage | Mode | After | Tasks (branch) | Deferred steps → stage`); `validate` compares that rendered table with the table under `## Execution schedule` in each of the eight wave files (ADR 0040 item 4). Add `pythonpath = ["."]` as the first line of `[tool.pytest.ini_options]` in the root `pyproject.toml`, and create `scripts/__init__.py` empty (size 0). Every script of this task starts its `scripts.*` imports after `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` (ADR 0040 item 9).

- [ ] **Step 3: Implement `scripts/check_ownership.py`** — changed files = `git diff --name-only --diff-filter=ACMRD --no-renames -z <base>...<branch>` split on NUL (renames are checked as delete plus add, ADR 0040 item 5); `--task <id>`: for a task that is sequential (no `owns`), exit 0; otherwise apply `owns` − `excludes` ∪ `always_allowed` with the pyproject/package.json and `__init__.py` special rules of overview §7.4; `--stage <id>`: a path passes when it is owned (`owns` − `excludes`) by at least one task of the stage or is always-allowed under the same special rules (ADR 0040 item 7). Exit codes 0, 1 and 2 and the output lines exactly as in "Interfaces".

- [ ] **Step 4: Implement `scripts/integration_gate.py`** — each check is a function `(ctx) -> CheckResult(name, status, reason, duration_s, output_tail)` (last 40 lines of output) with the check names of the "Interfaces" table; commands exactly as overview §7.7, run through `scripts.proc.run` with `check=False` inside `env --chdir <worktree>` with timeout 3600 s; applicability conditions evaluated from files on the branch checkout (the gate checks out `--branch` in a temporary worktree under `.swarm/worktrees/<stage>` with `git worktree add --detach` (`setup worktree` on failure), runs `uv sync --all-packages --frozen` there (`setup uv-sync` on failure), runs the checks there, and removes the worktree afterwards, so the coordinator's working tree is never modified). G1 calls `check_ownership.py --stage`. G9 collects counts on the base in a second temporary worktree `.swarm/worktrees/<stage>-base`. G10 compares only the `results` key. PR-body exemptions read from `--pr-body <file>`. The `except Exception as error:` that turns a crashing check into `fail` carries a same-line justification comment, not `# noqa: BLE001` (ADR 0040 item 1).

- [ ] **Step 5: Implement `scripts/cluster_smoke.py`** — waits for every ArgoCD Application in `argocd` to be `Synced/Healthy` (poll 15 s, `--timeout` default 1200 s), runs `scripts/doctor.py`'s memory check (≤ 9.5 GiB, imported lazily because `doctor.py` is created by W1-T06; before W1-T06 is merged the memory check is reported `skip`), then every check in `tests/smoke/*.yaml` (`http` checks never follow redirects, so `expect_status` may be a 3xx code; `exec` checks run in their required `namespace`); prints one line per check `PASS|FAIL <component>/<name>: <detail>`; exit 1 on any FAIL. The `subprocess.Popen` of the port-forward carries `# noqa: S603 - <justification>` on the line ruff reports (ADR 0040 item 1).

- [ ] **Step 6: Registry and smoke documentation** — `tests/registry/README.md` and `tests/smoke/README.md` state the formats of overview §7.7, the file-naming rule (`<TST-ID>--<task-id>.yaml`, `<component>.yaml`), who creates them (the task that introduces the test or deploys the component), and the exemption lines (`registry-removal:`, `test-removal:`, `baseline-change:`). `schema.json` files are JSON Schema draft 2020-12 for each format.

- [ ] **Step 7: `.gitattributes` and `.gitignore`** — append `wiki/log.md merge=union` to `.gitattributes`; append these three lines, in this order, to the end of `.gitignore` under a comment line `# Swarm state and tool outputs (W1-T16, ADR 0037)`: `.swarm/`, `.hypothesis/`, `coverage.xml`. (`.coverage` and `htmlcov/` are already ignored by the `# Python` block.)

- [ ] **Step 8: Run tests** → PASS; `uv run python scripts/swarm_schedule.py validate` → `schedule OK: 8 weeks, 39 stages, 94 tasks` (this includes the wave-table comparison of all eight wave files). The root `dev` dependency group line now reads `"pyyaml>=6,<7", "types-pyyaml", "pathspec>=0", "jsonschema>=0", "types-jsonschema",` (paragraph after Step 9); `uv run ruff check .` → `All checks passed!` with no `noqa` other than `# noqa: S603 - <justification>` (ADR 0040 item 1).

- [ ] **Step 9: Commit**

```bash
git add scripts tests/repo tests/registry tests/smoke .gitattributes .gitignore pyproject.toml uv.lock
git commit -m "build: add swarm schedule, ownership check and integration gate tooling

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

`versions.yaml` does not exist yet at this point (W1-T02 creates it in stage W1-P1); add `pathspec` and `jsonschema` to the root `dev` dependency group with the constraint `>=0` now, plus the type stubs `types-jsonschema` without a constraint (like `types-pyyaml`, needed by `mypy --strict` for `import jsonschema`), and W1-T02 step 6 aligns the constraint with the resolved version (W1-T02's version table gains rows `pathspec` (latest 0.x) and `jsonschema` (4.x)).

---

### Task W1-T02: Resolve and enforce pinned versions

**Requirement IDs:** GEN-050, GEN-051, PG-22.
**Depends on:** W1-T01. **Branch:** `feat/w1-versions`.

> **Amended 2026-11-27 after the W1-T02 implementation, per PG-22 (overview §5; ADR 0041).** The "Files" and "Interfaces" lists, the version table rows `pathspec`, `kubectl-image` and the image-row note, Steps 3, 4, 5, 6, 7, 8 and 9 were changed: Step 3's chart-row note, Step 4 (`scripts/check_versions.py`), Step 5 (pin date and chart-row rule), Step 6 (`pathspec`/`mypy`), Step 7 (`scripts/check_versions.py` run), Step 8 (the stub it replaces) and Step 9 (`wiki/versions.md` in `git add`). `wiki/versions.md` is in W1-T02's `owns` and in W1-T03's `excludes` in `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`. The `wiki/versions.md` stub is already on `develop` from the `docs/w1-t02-gaps` PR, and `feat/w1-versions` is rebased onto that `develop` before the ownership check ("W1-P1 integration steps" under "Execution schedule" above).

> **Amended 2026-11-27 after the W1-T14 review, per PG-26 (overview §5; ADR 0045 D6).** Step 8 (deferred to W1-S3) also writes the section `## GitHub Actions` of `wiki/versions.md` from the `uses:` lines of `.github/workflows/ci.yml`. Nothing else in W1-T02 changed.

**Files:**
- Create: `versions.yaml`, `scripts/check_versions.py`, `scripts/render_versions.py`, `scripts/versions_lib.py`
- Create (generated, committed): `deploy/root/files/versions.yaml`, `.github/versions.env`
- Keep: `wiki/versions.md`, the stub with exactly this content (three lines, LF line endings, final newline): line 1 `# Versions`, line 2 empty, line 3 `Status: not implemented yet — planned in W1-T02 step 8.` The stub already exists on `develop`: the planner committed it in the `docs/w1-t02-gaps` PR (PG-22, ADR 0041 decision 1), so the `wiki/index.md` link of W1-T03 resolves on every branch. W1-T02 keeps the identical file on `feat/w1-versions` (Step 9 `git add` still includes it; after the rebase of "W1-P1 integration steps" it is no longer in `git diff origin/develop...feat/w1-versions`, and the merge into `integration/w1-p1` is clean). W1-T03 does not create or edit this page (it is in W1-T03's `excludes`, PG-22); Step 8 replaces the stub in stage W1-S3
- Test: `tests/repo/test_versions.py`

**Interfaces:**
- Produces: `versions.yaml` schema below; `scripts.versions_lib.load_versions(path: Path = REPO/"versions.yaml") -> dict[str, Any]`; `scripts.versions_lib.version_of(key: str) -> str` (returns the string value, or the `version` field of a mapping); `uv run python scripts/render_versions.py [--check]`.
- Produces: CLI `uv run python scripts/check_versions.py` (no arguments; PG-22). It loads `versions.yaml` at the repository root with `load_versions()` and runs `validate()` over it. Output and exit codes:

| Case | Output (stderr) | Exit |
|---|---|---|
| No validation error | nothing | 0 |
| `validate()` returns one or more errors | one line per error, exactly the error string (format `<key>: <problem>`, for example `python: '3.11.9' does not match ^3\.12\.\d+$`), in the order `validate()` returns them | 1 |
| `versions.yaml` is missing or unreadable (`OSError`), is not valid YAML (`yaml.YAMLError`), or its top level is not a mapping (`ValueError`) | one line `versions.yaml: <exception text>`, where every run of whitespace in the exception text (newlines included) is replaced by one space, for example `versions.yaml: [Errno 2] No such file or directory: '/home/arkhash0309/projects/rootline/versions.yaml'` | 2 |

  It writes no file and makes no network call.

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
| `pathspec` | `0.12.1` (the latest 0.x release on 2026-11-27; 1.x exists and is outside the line). uv then resolves `mypy` to `1.19.1` inside the dev constraint `mypy>=1.18,<2`, because `mypy` 1.20 requires `pathspec` 1.x (PG-22) | gitignore-style globs for `scripts/check_ownership.py` (W1-T16) |
| `jsonschema` | 4.x | registry and smoke file validation (W1-T16) |
| `prometheus-operator-crds` | `{version, chart, repo}` latest stable chart | CRDs Application (W1-T10) |
| `postgres-image` | `{version: "16", repo: ghcr.io/cloudnative-pg/postgresql, digest}` | CNPG image (W1-T11) |
| `kubectl-image` | `{version: "1.36.<patch>", repo: "docker.io/rancher/kubectl", digest: "sha256:<64 hex>"}`: the highest Docker Hub tag `v1.36.<patch>` of `docker.io/rancher/kubectl` (same minor as `k3s` `v1.36.6+k3s1`), `version` is that tag without the leading `v`, `digest` is the multi-arch index digest of that tag. On 2026-11-27 this is tag `v1.36.2`, digest `sha256:06c7a7a9772737494ae1e0c3af90f1b5385630c147e47c1c7cea92f4bed55fbe`. The repo changed from `bitnami/kubectl` because `bitnami/kubectl` publishes only the tag `latest` (kubectl 1.37.3 on 2026-11-27) and has no 1.36 tag (PG-22, ADR 0041). The image contains only `/bin/kubectl` (no shell), so the `copy-ca` Job runs `kubectl` alone (W1-T10 Step 5) | `copy-ca` Job (W1-T10) |
| `busybox` | `{version: "1.37", repo: "docker.io/library/busybox", digest: "sha256:<64 hex>"}`. W1-T02 Step 5 records the 64-hex digest (the multi-arch index digest of tag `1.37`, "Image digest" lookup method); the implementer writes the concrete value | LAB-071 injection Job image |
| `uv-image`, `python-image`, `node-image`, `opa-image` | `{version, repo, digest}` | CI-020 digest-pinned base images |

Image rows (`postgres-image`, `kubectl-image`, `busybox`, `uv-image`, `python-image`, `node-image`, `opa-image`, and the `keycloak` and `keycloak-config-cli` mappings): `repo` is the fully qualified image repository, registry host included and tag excluded (PG-22). Docker Hub official images use `docker.io/library/<name>` (for example `docker.io/library/python`, `docker.io/library/busybox`), other Docker Hub images `docker.io/<namespace>/<name>` (for example `docker.io/openpolicyagent/opa`, `docker.io/rancher/kubectl`), other registries their own host (for example `ghcr.io/cloudnative-pg/postgresql`, `quay.io/keycloak/keycloak`). `digest` is the digest of the multi-arch index of the tag.

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies GEN-050."""
import re
from pathlib import Path

from scripts.versions_lib import CONSTRAINTS, load_versions, validate, version_of

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
    import subprocess
    import sys

    r = subprocess.run([sys.executable, "scripts/render_versions.py", "--check"], cwd=REPO)
    assert r.returncode == 0
```

The `subprocess.run` line carries no `noqa`: ruff `0.17.6` does not report `S603` for this argument list, and a `# noqa: S603` there fails with `RUF100` (ADR 0040 item 1, verified 2026-11-27).

`scripts/__init__.py` (empty, size 0) and `pythonpath = ["."]` in `[tool.pytest.ini_options]` of the root `pyproject.toml` already exist on `develop`: W1-T16 (stage W1-S2) created both. This step only verifies them: `test -f scripts/__init__.py && test ! -s scripts/__init__.py` exits 0, and `grep -n '^pythonpath = \["."\]$' pyproject.toml` prints one line. If either check fails, stop and report `BLOCKED`; do not create or edit either file (both already exist, and a change to `pyproject.toml` outside its dependency arrays is outside W1-T02's `owns`, overview §7.4).

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

For chart entries, `version` holds the value that the key's GEN-050 line constrains, and `CONSTRAINTS` applies to `version` (PG-22). The full rule is in Step 5 "Chart rows".

- [ ] **Step 4: Implement `scripts/render_versions.py` and `scripts/check_versions.py`**

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

`scripts/check_versions.py` (PG-22, ADR 0041): CLI `uv run python scripts/check_versions.py`, no arguments. It runs `validate()` over `versions.yaml`; prints one line per error to stderr; exits 0 if there are no errors, 1 if there are validation errors, 2 if the file is missing or unreadable, is not valid YAML, or is not a mapping. The exact behaviour table is in "Interfaces" above. Final text:

```python
"""Validate versions.yaml against the GEN-050 version lines.

Usage: uv run python scripts/check_versions.py
Exit codes: 0 every key is present and satisfies its line; 1 at least one error (one stderr line per
error, format `<key>: <problem>`); 2 versions.yaml is missing or unreadable, is not valid YAML, or is
not a mapping (one stderr line).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.versions_lib import load_versions, validate


def main() -> int:
    try:
        data = load_versions()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        # a yaml.YAMLError message spans several lines; the contract is one stderr line
        print(f"versions.yaml: {' '.join(str(exc).split())}", file=sys.stderr)
        return 2
    errors = validate(data)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Verification: `uv run python scripts/check_versions.py; echo $?` prints `0` once `versions.yaml` is complete (Step 7).

- [ ] **Step 5: Resolve versions on the pin date and write `versions.yaml`**

The pin date of W1-T02 is **2026-11-27**, the date of the lookup (PG-22): `versions.yaml` has `pin_date: "2026-11-27"`, and every version and digest in it is the result of a lookup made on 2026-11-27.

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

Chart rows (PG-22). A chart entry is a mapping `{version, chart, app, repo}`: `version` holds the value that the key's GEN-050 line constrains, and the `CONSTRAINTS` regex applies to it; `chart` holds the Helm chart version; `app` holds the application version (the chart's `appVersion`): it MUST be written when the application version differs from the value in `version`, and MAY be written when the two are equal (for example `chaos-mesh` `{version: "2.8.8", chart: "2.8.8", app: "2.8.8"}`); `repo` is the Helm repository URL.

| Key | GEN-050 line is on | `version` = | Example on 2026-11-27 |
|---|---|---|---|
| `argo-cd` | application (`argo-cd` (app) 3.x) | application version | `{version: "3.6.3", chart: "10.20.0", repo: "https://argoproj.github.io/argo-helm"}` |
| `traefik` | application (Traefik 3.x) | application version | `{version: "3.8.0", chart: "43.0.0", repo: "https://traefik.github.io/charts"}` |
| `kube-prometheus-stack`, `loki`, `tempo`, `opentelemetry-collector`, `chaos-mesh`, `kyverno`, `external-secrets`, `cert-manager`, `cloudnative-pg`, `opentelemetry-demo`, and the extra key `prometheus-operator-crds` | chart | chart version (equal to `chart`) | `loki`: `{version: "6.55.0", chart: "6.55.0", app: "3.6.7", repo: "https://grafana.github.io/helm-charts"}` |

For `opentelemetry-demo`, the value is exactly `{version: "0.42.8", chart: "0.42.8", app: "3.1.0", repo: "https://open-telemetry.github.io/opentelemetry-helm-charts"}` (the regex applies to `version`, which equals the chart version).

`mcp` rule: pick the newest release whose README or changelog lists protocol revision `2026-07-28`. If none does, pin the newest release, set `mcp_protocol_revision: "2025-11-25"` in `versions.yaml`, and the W1-T04 ADR 0012 records the fallback (GEN-050).

- [ ] **Step 6: Align `pyproject.toml` constraints**

For every Python dependency, set the constraint in the member that uses it to `>=<resolved>,<<next major>>` (for 0.x packages: `>=<resolved>,<0.<minor+1>>`). `pathspec` is pinned to `0.12.1`, the latest 0.x release on 2026-11-27, so the root `dev` group constraint is `pathspec>=0.12.1,<0.13` (PG-22). The `mypy` constraint stays `mypy>=1.18,<2`; inside it uv resolves `mypy` `1.19.1`, because `mypy` 1.20 requires `pathspec` 1.x. This is expected and is not a failure of this step. Run `uv lock` and verify `uv.lock` resolves each to the version in `versions.yaml`: `uv run python -c "import tomllib;print([p['version'] for p in tomllib.load(open('uv.lock','rb'))['package'] if p['name']=='fastapi'])"`.

- [ ] **Step 7: Render and test**

Run: `uv run python scripts/render_versions.py`, then `uv run python scripts/check_versions.py` → no output, exit 0, then `uv run pytest tests/repo/test_versions.py -v` → PASS.

- [ ] **Step 8: Write `wiki/versions.md`** (deferred to stage W1-S3, overview §7.3; the stub is on `develop` from the `docs/w1-t02-gaps` PR, "Files" above, PG-22)

Replace the stub's content with: a heading `# Versions`, the line `Pin date: <pin_date>`, a table `| Key | Version | Chart | Source command |` with one row per `versions.yaml` key, a section `## GitHub Actions`, and a section `## Upgrade rule` quoting GEN-051.

`## GitHub Actions` (amended 2026-11-27, PG-26, ADR 0045 D6): a table `| Action | Tag | Commit SHA |` copied from `.github/workflows/ci.yml` on `origin/develop` at the start of W1-S3 (W1-T14 merged with stage W1-P3, so the file exists). A `uses:` line is a line matching `^\s*(-\s+)?uses:`; every such line MUST match `^\s*(-\s+)?uses:\s+([\w.-]+/[\w.-]+)@([0-9a-f]{40})\s+#\s+(v\S+)\s*$` (group 2 = `Action`, group 3 = `Commit SHA`, group 4 = `Tag`). One row per distinct `Action`, rows sorted by `Action`. If `ci.yml` is absent, a `uses:` line does not match, or one `Action` appears with two different SHAs, Step 8 reports `STATUS: BLOCKED` with that line and the coordinator sends W1-T14 back to its implementer. Every PR merged after this step that changes an action SHA in `ci.yml` MUST update the matching row in the same PR (GEN-051).

- [ ] **Step 9: Commit** (made at the end of step 7, per overview §7.3; step 8 commits separately on `feat/w1-versions-deferred`)

```bash
git add versions.yaml scripts/ deploy/root/files/versions.yaml .github/versions.env pyproject.toml uv.lock tests/repo/test_versions.py wiki/versions.md libs services eval
git commit -m "build: pin versions in versions.yaml and render derived files

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task W1-T03: Wiki skeleton and wiki lint

**Requirement IDs:** WIK-001, WIK-002, WIK-010, WIK-012, WIK-013, WIK-020, WIK-021, GEN-040, CST-012.
**Depends on:** W1-T01. **Parallel-safe** with W1-T02. **Branch:** `feat/w1-wiki`.

**Files:**
- Create: every file in the WIK-002 tree except `wiki/adr/0001…` (W1-T04), `wiki/adr/0037…0041` (already on `develop`, PG-18 … PG-22; do not edit) and `wiki/versions.md` (the stub is on `develop` from the `docs/w1-t02-gaps` PR and is owned by W1-T02; in W1-T03's `excludes`, PG-22)
- Create: `wiki/components/<slug>.md` for each slug in `COMPONENT_PAGES` below
- Create: `scripts/wiki_lint.py`
- Test: `tests/repo/test_wiki_lint.py`

Base (PG-22, ADR 0041): `feat/w1-wiki` and `integration/w1-p1` start from the first `origin/develop` commit that contains `wiki/adr/0041-w1-t02-version-gaps.md` (the squash merge of `docs/w1-t02-gaps`), not from `f85bb63`. The coordinator records that commit as the W1-P1 stage base in `.swarm/stages/W1-P1.json` before it dispatches W1-T03 and before it creates `integration/w1-p1`. `scripts/check_ownership.py` reads the schedule YAML from the checkout it runs in, so `feat/w1-versions` (W1-T02, branched from `f85bb63`) sees the new W1-T02 `owns` only after a rebase: after the `docs/w1-t02-gaps` PR merges to develop, the W1-T02 implementer rebases `feat/w1-versions` onto the new `origin/develop` (`git rebase origin/develop`; the rebase is clean because the PR touches only plans, spec, ADR and `wiki/versions.md`), then pushes with `git push --force-with-lease origin feat/w1-versions`. Only then is `check_ownership.py --task W1-T02 --base origin/develop --branch HEAD` run in the W1-T02 worktree (full sequence: "W1-P1 integration steps" under "Execution schedule" above). If `feat/w1-wiki` already exists on an older base, the W1-T03 implementer rebases it onto the new stage base before Step 5.

`scripts/wiki_lint.py` runs `git` through `scripts.proc.run` (created by W1-T16) and the test imports no `subprocess`, so both files pass `uv run ruff check` (after `uv run ruff format`) with no finding and without any `noqa` (PG-21, ADR 0040 items 1 and 9).

**Interfaces:**
- Produces: `uv run python scripts/wiki_lint.py [--changed-files <file>] [--pr-body <file>]` exit 0/1, one line per problem `wiki-lint: <rule>: <detail>`; constant `COMPONENT_PAGES`.

`COMPONENT_PAGES` (one file each in `wiki/components/`): `console`, `api`, `agent`, `gate`, `faultlab`, `mcp-telemetry`, `mcp-k8s`, `mcp-gitops`, `migrate`, `demo-seed`, `postgres`, `keycloak`, `keycloak-config`, `otel-collector`, `kube-prometheus-stack`, `loki`, `tempo`, `argocd`, `chaos-mesh`, `kyverno`, `external-secrets`, `cert-manager`, `traefik`, `workload`, plus the extra pages `telemetry`, `capacity`.

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies WIK-020, WIK-021."""
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
    index = "# Index\n" + "".join(f"- [{f}]({f})\n" for f in [*files, "index.md", "status.md"])
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
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

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
    out = run(["git", "-C", str(REPO), "log", "-1", "--format=%cs", "--", *CODE_PREFIXES],
              check=False).stdout.strip()
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
| `wiki/index.md` | `# Rootline wiki`, a paragraph quoting WIK-001's spec/wiki split, then one bullet per wiki file: `- [<path>](<path>) — <one-line description>`. "Every wiki file" includes `adr/0037-swarm-state-dir.md`, `adr/0038-ruff-scope-and-formatting.md`, `adr/0039-commit-trailers.md`, `adr/0040-swarm-plan-amendments-w1-t16.md` and `adr/0041-w1-t02-version-gaps.md`, which are on `develop` before this task starts (PG-18 … PG-22); without their bullets `wiki_lint.py` reports `index-missing` for them. It also includes `versions.md` (bullet `- [versions.md](versions.md) — pin date and resolved versions (GEN-050)`); the file is the W1-T02 stub already on `develop`, which this task does not create or edit (PG-22) |
| `wiki/status.md` | WIK-012 format; `## Current milestone: Week 1 — Foundations`; In progress lists W1 tasks; Blockers `None` |
| `wiki/log.md` | `# Log` then `## <today>` and `- [agent] Created wiki skeleton (W1-T03)` |
| `wiki/architecture.md` | the spec §5.1 diagram verbatim in a code block; a table `| Component | Namespace | Spec | Wiki page |` for ARC-001 |
| `wiki/glossary.md` | the spec §2 table verbatim plus a `## Additions` section (empty table header) |
| `wiki/cost-ledger.md` | `# Cost ledger`; the CST-001 caps table; a weekly table `| Week of (Monday) | Anthropic dev | Anthropic cluster | Anthropic CI | Ledger dev/eval/ci | GCP to date | Total | Variance vs plan | Notes |` with the first row for week 1 at 0.00 |
| `wiki/adr/0000-template.md` | WIK-011 template: `# NNNN — <title>`, `Status: proposed`, `Date:`, `## Context`, `## Decision`, `## Consequences`, `## Alternatives considered`, `## Spec references` |
| `wiki/components/<slug>.md` | WIK-010 nine headings in order (Purpose, Requirement IDs, Interfaces, Configuration, Dependencies, Data owned, Failure modes and handling, Runbook links, Last verified) |
| `wiki/runbooks/workstation-setup.md` | sections in order: `## Windows side` (WSL 2 with distribution `Ubuntu` 26.04 LTS, the exact GEN-040 `.wslconfig` content, `wsl --shutdown`, the browser); `## WSL basics` (`/etc/wsl.conf` with `[boot] systemd=true` and `[user] default=arkhash0309`, `sudo apt update && sudo apt upgrade -y`, the support packages of GEN-040); `## Tools` — one subsection per GEN-040 row with the exact commands used on 2026-11-26 (root part: the script `~/rootline-root-setup.sh` — apt packages including `docker-buildx`, `[interop] appendWindowsPath=false`, Ollama installer with the service disabled; user part: release binaries into `~/.local/bin`, uv + Python 3.12, fnm + Node 24, the gcloud tarball with `gke-gcloud-auth-plugin`, the Linux Claude Code build; `gh` logged in as `arkhash0309` with `gh auth setup-git`; added in week 6: `npx playwright install --with-deps chromium`); `## Repositories` (clone into `/home/arkhash0309/projects/rootline` and `/home/arkhash0309/projects/rootline-env`, never under `/mnt/c`; VS Code users open them with the Remote - WSL extension); a section `## Anthropic` describing O-8 and PG-13; a section `## Verify` saying run `task doctor` |
| `wiki/versions.md` | the W1-T02 stub, already on `develop` from the `docs/w1-t02-gaps` PR: do not create or edit it; list it in `index.md` (PG-22) |
| `wiki/runbooks/local-up.md` | already created by W1-T08 (stage W1-S2): do not create or edit it; list it in `index.md` |
| `wiki/runbooks/capture-batch.md`, `gcp-bootstrap.md`, `gke-spin-up.md`, `gke-teardown.md`, `github-apps.md`, `interview-demo.md`, `recovery.md` | title + `Status: not implemented yet — planned in <task>` (capture-batch: W2-T12; gcp-bootstrap: W7-T01; gke-spin-up/teardown: W7-T06; github-apps: W2-T07 and W3-T10; interview-demo: W8-T06; recovery: W2-T12) |
| `wiki/security/threat-model.md` | the SEC-140 table verbatim; `Status: summary only — full STRIDE in W8-T04` |
| `wiki/eval/dataset.md`, `local-pilot.md`, `results.md` | title + status line (W2-T13, W4-T14, W4-T15) |

- [ ] **Step 6: Run the lint for real**

Run: `uv run python scripts/wiki_lint.py`
Expected: only `missing-adr: 0001` … `missing-adr: 0025` (fixed by W1-T04). No `broken-link: index.md -> versions.md` line appears: the `wiki/versions.md` stub is on the stage base from the `docs/w1-t02-gaps` PR (PG-22). Do not merge this PR until W1-T04 is merged into the same branch, or merge W1-T04 first. **Ordering rule:** create W1-T04 on top of this branch (`feat/w1-wiki`) and open a single PR for W1-T03 + W1-T04.

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
- Do not create, edit or renumber: `wiki/adr/0037-swarm-state-dir.md`, `wiki/adr/0038-ruff-scope-and-formatting.md`, `wiki/adr/0039-commit-trailers.md`, `wiki/adr/0040-swarm-plan-amendments-w1-t16.md`. The planner wrote 0037 … 0039 on 2026-11-26 (branch `docs/w1-plan-gaps`, PG-18 … PG-20) and 0040 on 2026-11-27 (branch `docs/w1-t16-decisions`, PG-21), so all four are on `develop` before stage W1-P1 starts. Their spec §26 rows already link them; leave those four rows unchanged. Also do not create, edit or renumber `wiki/adr/0041-w1-t02-version-gaps.md`: the planner wrote it on 2026-11-27 (branch `docs/w1-t02-gaps`, PG-22), it is on `develop` before this task's PR merges, and its spec §26 row already links it; leave that row unchanged. The next free ADR number after this task is **0042**.

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

Run: `uv run python scripts/wiki_lint.py` → no output and exit 0, both on `feat/w1-wiki` alone (the `wiki/versions.md` stub is on the stage base from the `docs/w1-t02-gaps` PR, PG-22) and on `integration/w1-p1` after both W1-P1 PRs are merged (gate check G11).
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

  > **Amended 2026-11-27, per PG-23 (overview §5; ADR 0042).** The `writing-skills` skill is not available to the coordinator, so it is not loaded in Step 1 or Step 4. Step 1 is the baseline scenario run of ADR 0042 D2 to D5: one fresh `rootline-implementer` (`model: "sonnet"`, `effort: "high"`, `isolation: "worktree"`) with the fixed prompt of ADR 0042 D2 step 3, the record `.swarm/gates/W1-T05-baseline.json` (fields in ADR 0042 D3), one retry for an invalid attempt, and `BLOCKED` (stage W1-P2 stops for the owner) after a second invalid attempt. Step 1 writes nothing to `wiki/log.md`. The coordinator passes the record JSON to the W1-T05 implementer in `details`; a `baseline-passes` result changes nothing in Steps 2, 3 and 5. Step 4 is the verification scenario run of ADR 0042 D6, recorded in `.swarm/gates/W1-T05-verify.json`, with the `wiki/log.md` line of ADR 0042 D6 step 3 on `feat/w1-wiki-skill-deferred`. The red-green test of Steps 2 and 5 is unchanged.

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

This is the final text, already in `ruff format` output, including the one lint suppression allowed by PG-21 / ADR 0040 item 1: `# noqa: S603` with its justification on the same line (ruff `0.17.6` reports `S603` on the `subprocess.run(` line because `cmd` is a parameter). `uv run ruff check scripts/proc.py` → `All checks passed!` (verified 2026-11-27). Confirm with `diff` against this block; a difference other than what `ruff format` produces means W1-T16 is not merged as planned: report `BLOCKED`.

```python
"""Subprocess helper used by every Taskfile script (GEN-041)."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    env: Mapping[str, str] | None = None,
    timeout: int = 600,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(  # noqa: S603 - cmd is an argument list run without a shell (GEN-041)
        cmd, check=check, capture_output=capture, text=True, env=full_env, timeout=timeout, input=input_text
    )
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    location = "WSL filesystem"
    if on_windows_fs:
        location = "Windows filesystem: move to /home/arkhash0309/projects"
    out.append(Check("repo-location", "FAIL" if on_windows_fs else "OK", f"{repo} ({location})"))
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

> **Amended 2026-11-27 after the W1-T07 review, per PG-24 (overview §5; ADR 0043 `wiki/adr/0043-w1-t07-review-decisions.md`).** The review of `feat/w1-py-common` at `c91ea10` found seven plan-text defects. The "Files" `pyproject.toml` line, the Step 1 test blocks `test_timeutil.py`, `test_problem.py`, `test_health.py` and `test_requestid.py`, and the Step 3 blocks `timeutil.py`, `problem.py`, `health.py` and `requestid.py` were changed to carry these decisions. The planner ran the changed blocks on 2026-11-27 (Python `3.12.16`, `fastapi` `0.165.0`, `starlette` `1.10.0`, `httpx` `0.29.0`, `prometheus-client` `0.26.0`, `python-ulid` `3.2.1`): every test passes and `mypy` with `strict = true` reports no issue; the new and changed tests in `test_problem.py`, `test_requestid.py` and `test_timeutil.py` fail on the `c91ea10` modules. The implementer copies the blocks' content and then runs `uv run ruff format` and `uv run ruff check` on each file (Global Constraints "Formatting", PG-19):
> - **D1 (version bounds).** W1-T02 Step 6 applies unchanged: a 0.x package gets `>=<resolved>,<0.<minor+1>>`, any other package `>=<resolved>,<<major+1>>`. The dependency list of `libs/py-common/pyproject.toml` is exactly the "Files" list below; on `c91ea10` only `fastapi` (`<1`), `prometheus-client` (`<1`) and `httpx` (`<1`) were wrong.
> - **D2 (request ID on a 500).** `RequestIdMiddleware` stores the resolved ID at `scope["state"]["request_id"]` (it creates `scope["state"] = {}` when the key is absent) before it calls the app. The `Exception` handler `_internal` runs in Starlette's `ServerErrorMiddleware`, outside `RequestIdMiddleware`, so it reads that value, logs the error with `request_id_var` set to it, returns it as `request_id` in the body and adds the response header `X-Request-Id` with it. The body helper's request ID is, in order: `scope["state"]["request_id"]`, then `request_id_var.get()`, then a new ULID. Test: `test_problem.py::test_internal_error_carries_incoming_request_id`.
> - **D3 (HTTP exceptions).** `install_problem_handlers` also registers a handler for `starlette.exceptions.HTTPException` (which covers `fastapi.HTTPException`) that returns `application/problem+json` and keeps the exception's headers. Statuses map through `HTTP_STATUS_PROBLEMS`: `401` `unauthenticated` "Unauthenticated", `403` `forbidden` "Forbidden", `404` `not_found` "Not found", `405` `method_not_allowed` "Method not allowed"; `detail` is the exception's string detail truncated to 500 characters. Every other status keeps its status and gets code `internal`, title "Internal error", detail "unexpected error" and one `WARNING` log line; `204` and `304` return an empty body. `PROBLEM_CODES` gains `"method_not_allowed": 405` (spec API-002 table row added by PG-24).
> - **D4 (non-UTF-8 request ID).** The middleware takes the first `x-request-id` header of `scope["headers"]` and decodes it with `latin-1`; a value that is not a ULID (`is_ulid` is false) is replaced by `new_ulid()` (API-004, unchanged).
> - **D5 (reserved `extra` keys).** `Problem(extra=...)` and the body helper drop the keys `type`, `title`, `status`, `detail`, `instance`, `code`, `request_id` (`RESERVED_PROBLEM_KEYS`) silently; no error is raised.
> - **D6 (naive datetimes).** `to_rfc3339` raises `ValueError("naive datetime not allowed: <dt.isoformat()>")` for a datetime whose `utcoffset()` is `None`; `parse_rfc3339` raises `ValueError("naive datetime not allowed: <text>")` for a string without an offset or `Z`.
> - **D7 (health router).** `make_health_router` serves `/healthz`, `/readyz` and `/metrics`. `make_metrics_route()` exists only for an app that does not include the health router; an app MUST NOT include both.

**Files:**
- Create: `libs/py-common/rootline_common/{ids,timeutil,logging,problem,health,requestid,otel,settings}.py`
- Modify: `libs/py-common/pyproject.toml` `[project] dependencies`, exactly these eleven lines in this order (constraint rule of W1-T02 Step 6; resolved versions from `versions.yaml` on 2026-11-27; PG-24 D1): `fastapi>=0.165.0,<0.166`, `pydantic>=2.14.4,<3`, `pydantic-settings>=2.16.3,<3`, `python-ulid>=3.2.1,<4`, `prometheus-client>=0.26.0,<0.27`, `opentelemetry-sdk>=1.45.2,<2`, `opentelemetry-exporter-otlp-proto-grpc>=1.45.2,<2`, `opentelemetry-instrumentation-fastapi>=0.66b0,<0.67`, `opentelemetry-instrumentation-httpx>=0.66b0,<0.67`, `opentelemetry-instrumentation-psycopg>=0.66b0,<0.67`, `httpx>=0.29.0,<0.30`
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
"""Verifies API-006, MCP-002 timestamp format and PG-24 D6."""
from datetime import UTC, datetime, timedelta, timezone

import pytest

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


def test_to_rfc3339_rejects_naive() -> None:
    with pytest.raises(ValueError, match=r"^naive datetime not allowed: 2026-11-30T09:05:07$"):
        to_rfc3339(datetime(2026, 11, 30, 9, 5, 7))


def test_parse_rejects_missing_offset() -> None:
    with pytest.raises(ValueError, match=r"^naive datetime not allowed: 2026-11-30T09:05:07$"):
        parse_rfc3339("2026-11-30T09:05:07")
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
"""Verifies API-002, API-004 (request ID on 500) and PG-24 D2, D3, D5."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from rootline_common.ids import is_ulid
from rootline_common.logging import configure_logging
from rootline_common.problem import (
    HTTP_STATUS_PROBLEMS,
    PROBLEM_CODES,
    Problem,
    install_problem_handlers,
)
from rootline_common.requestid import RequestIdMiddleware

RID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def make_app() -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)

    class Body(BaseModel):
        n: int

    @app.get("/boom")
    def boom() -> None:
        raise Problem("invalid_transition", 409, "Invalid transition", "queued -> merged")

    @app.post("/validate")
    def validate(body: Body) -> dict[str, object]:
        return {}

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret detail")

    @app.get("/auth")
    def auth() -> None:
        raise HTTPException(401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/teapot")
    def teapot() -> None:
        raise HTTPException(418, detail="teapot detail")

    @app.get("/extra")
    def extra() -> None:
        raise Problem("conflict", 409, "Conflict", "key reused",
                      extra={"status": 200, "code": "x", "request_id": "y", "hint": "h"})

    return app


def make_app_with_request_id() -> FastAPI:
    app = make_app()
    app.add_middleware(RequestIdMiddleware)
    return app


def test_problem_shape() -> None:
    r = TestClient(make_app()).get("/boom", headers={"X-Request-Id": RID})
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


def test_internal_error_carries_incoming_request_id(capsys: pytest.CaptureFixture[str]) -> None:
    """PG-24 D2: header, body request_id, incoming X-Request-Id and the log line agree."""
    configure_logging("test", "INFO")
    c = TestClient(make_app_with_request_id(), raise_server_exceptions=False)
    r = c.get("/crash", headers={"X-Request-Id": RID})
    assert r.status_code == 500
    assert r.headers.get_list("x-request-id") == [RID]
    assert r.json()["request_id"] == RID
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{")]
    assert [x["request_id"] for x in lines if x["logger"] == "rootline.problem"] == [RID]


def test_internal_error_generated_request_id_matches() -> None:
    c = TestClient(make_app_with_request_id(), raise_server_exceptions=False)
    r = c.get("/crash")
    assert r.headers.get_list("x-request-id") == [r.json()["request_id"]]
    assert is_ulid(r.json()["request_id"])


def test_not_found_is_problem() -> None:
    r = TestClient(make_app_with_request_id()).get("/nope", headers={"X-Request-Id": RID})
    assert r.status_code == 404 and r.headers["content-type"] == "application/problem+json"
    assert r.json() == {"type": "https://rootline.dev/problems/not_found", "title": "Not found",
                        "status": 404, "detail": "Not Found", "instance": "/nope",
                        "code": "not_found", "request_id": RID}
    assert r.headers.get_list("x-request-id") == [RID]


def test_method_not_allowed_keeps_allow_header() -> None:
    r = TestClient(make_app()).post("/boom")
    assert r.status_code == 405 and r.headers["allow"] == "GET"
    assert (r.json()["code"], r.json()["title"]) == ("method_not_allowed", "Method not allowed")


def test_http_401_maps_to_unauthenticated_and_keeps_headers() -> None:
    r = TestClient(make_app()).get("/auth")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    body = r.json()
    assert (body["code"], body["title"], body["detail"]) == ("unauthenticated", "Unauthenticated",
                                                             "Not authenticated")


def test_unmapped_http_status_is_internal_with_status_kept() -> None:
    r = TestClient(make_app()).get("/teapot")
    assert r.status_code == 418 and r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert (body["status"], body["code"], body["title"], body["detail"]) == (
        418, "internal", "Internal error", "unexpected error")
    assert "teapot detail" not in r.text


def test_reserved_extra_keys_are_dropped() -> None:
    r = TestClient(make_app()).get("/extra", headers={"X-Request-Id": RID})
    body = r.json()
    assert r.status_code == 409
    assert (body["status"], body["code"], body["hint"]) == (409, "conflict", "h")
    assert body["request_id"] != "y"
    assert Problem("conflict", 409, "Conflict", extra={"title": "x", "hint": "h"}).extra == {"hint": "h"}


def test_codes_table() -> None:
    assert PROBLEM_CODES == {
        "unauthenticated": 401, "insufficient_user_authentication": 401, "forbidden": 403,
        "not_found": 404, "method_not_allowed": 405, "validation_error": 422,
        "invalid_transition": 409, "conflict": 409, "separation_of_duties": 403,
        "rate_limited": 429, "lab_busy": 409, "internal": 500}
    assert HTTP_STATUS_PROBLEMS == {
        401: ("unauthenticated", "Unauthenticated"), 403: ("forbidden", "Forbidden"),
        404: ("not_found", "Not found"), 405: ("method_not_allowed", "Method not allowed")}
    assert all(PROBLEM_CODES[code] == status for status, (code, _) in HTTP_STATUS_PROBLEMS.items())
```

`libs/py-common/tests/test_health.py`:

```python
"""Verifies ARC-020 and PG-24 D7."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rootline_common.health import make_health_router, make_metrics_route


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


def test_health_router_serves_metrics_once() -> None:
    """PG-24 D7: make_health_router mounts /metrics itself, exactly once."""
    paths = [getattr(r, "path", None) for r in make_health_router({}).routes]
    assert sorted(p for p in paths if p) == ["/healthz", "/metrics", "/readyz"]


def test_metrics_route_standalone() -> None:
    app = FastAPI()
    app.router.routes.append(make_metrics_route())
    r = TestClient(app).get("/metrics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
```

`libs/py-common/tests/test_requestid.py`:

```python
"""Verifies API-004 and PG-24 D2, D4."""
import asyncio

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from rootline_common.ids import is_ulid
from rootline_common.logging import request_id_var
from rootline_common.requestid import RequestIdMiddleware

RID_A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
RID_B = "01BX5ZZKBKACTAV9WEVGEMMVRZ"


def make() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/x")
    def x(request: Request) -> dict[str, object]:
        return {"rid": request_id_var.get(), "state": request.state.request_id}

    return TestClient(app)


def call_raw(headers: list[tuple[bytes, bytes]]) -> tuple[list[Message], Scope]:
    """Drive the middleware with a raw ASGI scope (bytes headers, no client re-encoding)."""
    sent: list[Message] = []
    scope: Scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(RequestIdMiddleware(app)(scope, receive, send))
    return sent, scope


def test_valid_incoming_id_is_kept() -> None:
    r = make().get("/x", headers={"X-Request-Id": RID_A})
    assert r.headers["X-Request-Id"] == RID_A == r.json()["rid"] == r.json()["state"]


def test_invalid_incoming_id_is_replaced() -> None:
    r = make().get("/x", headers={"X-Request-Id": "abc"})
    assert r.headers["X-Request-Id"] != "abc" and is_ulid(r.headers["X-Request-Id"])
    assert r.json()["state"] == r.headers["X-Request-Id"]


def test_non_utf8_incoming_id_is_replaced() -> None:
    sent, scope = call_raw([(b"x-request-id", b"\xff\xfe01ARZ3NDEKTSV4RRFFQ69G5F")])
    rid = dict(sent[0]["headers"])[b"x-request-id"].decode()
    assert is_ulid(rid) and scope["state"]["request_id"] == rid


def test_first_incoming_header_wins() -> None:
    sent, scope = call_raw([(b"x-request-id", RID_A.encode()), (b"x-request-id", RID_B.encode())])
    assert dict(sent[0]["headers"])[b"x-request-id"] == RID_A.encode()
    assert scope["state"]["request_id"] == RID_A
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
"""Time helpers: RFC 3339 UTC with Z (API-006, MCP-002, PG-24)."""
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_rfc3339(dt: datetime, *, ms: bool = True) -> str:
    if dt.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {dt.isoformat()}")
    dt = dt.astimezone(UTC)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{dt.microsecond // 1000:03d}Z" if ms else f"{base}Z"


def parse_rfc3339(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {text}")
    return dt.astimezone(UTC)
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
"""RFC 9457 problem+json (API-002, PG-24)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from rootline_common.ids import new_ulid
from rootline_common.logging import request_id_var

PROBLEM_CODES: dict[str, int] = {
    "unauthenticated": 401, "insufficient_user_authentication": 401, "forbidden": 403,
    "not_found": 404, "method_not_allowed": 405, "validation_error": 422,
    "invalid_transition": 409, "conflict": 409, "separation_of_duties": 403,
    "rate_limited": 429, "lab_busy": 409, "internal": 500,
}
# HTTPException status -> (code, title) (PG-24 D3). Any other status: code "internal", status kept.
HTTP_STATUS_PROBLEMS: dict[int, tuple[str, str]] = {
    401: ("unauthenticated", "Unauthenticated"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not found"),
    405: ("method_not_allowed", "Method not allowed"),
}
# Body keys that `extra` can never set (PG-24 D5); they are dropped silently.
RESERVED_PROBLEM_KEYS: frozenset[str] = frozenset(
    {"type", "title", "status", "detail", "instance", "code", "request_id"})
log = logging.getLogger("rootline.problem")


def _clean(extra: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (extra or {}).items() if k not in RESERVED_PROBLEM_KEYS}


class Problem(Exception):
    def __init__(self, code: str, status: int, title: str, detail: str = "",
                 extra: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> None:
        super().__init__(detail or title)
        self.code, self.status, self.title, self.detail = code, status, title, detail[:500]
        self.extra, self.headers = _clean(extra), headers or {}


def _request_id(request: Request) -> str:
    """scope["state"]["request_id"] (RequestIdMiddleware), else request_id_var, else a new ULID (PG-24 D2)."""
    state = request.scope.get("state")
    rid = state.get("request_id") if isinstance(state, dict) else None
    if isinstance(rid, str) and rid:
        return rid
    return request_id_var.get() or new_ulid()


def _body(request: Request, code: str, status: int, title: str, detail: str,
          extra: dict[str, Any] | None = None, request_id: str | None = None) -> dict[str, Any]:
    return {"type": f"https://rootline.dev/problems/{code}", "title": title, "status": status,
            "detail": detail, "instance": request.url.path, "code": code,
            "request_id": request_id or _request_id(request), **_clean(extra)}


def _resp(body: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(body, status_code=body["status"], media_type="application/problem+json",
                        headers=headers)


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def _problem(request: Request, exc: Problem) -> JSONResponse:
        return _resp(_body(request, exc.code, exc.status, exc.title, exc.detail, exc.extra), exc.headers)

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> Response:
        headers = dict(exc.headers) if exc.headers else None
        if exc.status_code in (204, 304):  # no body allowed (RFC 9110 §15.3.5, §15.4.5)
            return Response(status_code=exc.status_code, headers=headers)
        mapped = HTTP_STATUS_PROBLEMS.get(exc.status_code)
        if mapped is None:
            log.warning("unmapped HTTPException status %d", exc.status_code)
            body = _body(request, "internal", exc.status_code, "Internal error", "unexpected error")
        else:
            detail = exc.detail[:500] if isinstance(exc.detail, str) else ""
            body = _body(request, mapped[0], exc.status_code, mapped[1], detail)
        return _resp(body, headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return _resp(_body(request, "validation_error", 422, "Validation error",
                           "request body or query is invalid", {"errors": errors}))

    @app.exception_handler(Exception)
    async def _internal(request: Request, exc: Exception) -> JSONResponse:
        # Runs in ServerErrorMiddleware, outside RequestIdMiddleware: request_id_var is already
        # reset and the response bypasses the middleware's send wrapper (PG-24 D2).
        rid = _request_id(request)
        token = request_id_var.set(rid)
        try:
            log.error("unhandled error", exc_info=exc)
        finally:
            request_id_var.reset(token)
        return _resp(_body(request, "internal", 500, "Internal error", "unexpected error", request_id=rid),
                     {"X-Request-Id": rid})
```

`health.py`:

```python
"""/healthz, /readyz, /metrics (ARC-020, PG-24 D7)."""
from collections.abc import Awaitable, Callable, Mapping

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


async def _metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def make_metrics_route() -> APIRoute:
    """`GET /metrics` alone, for an app that does not include make_health_router (PG-24 D7)."""
    return APIRoute("/metrics", _metrics, methods=["GET"], include_in_schema=False)


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
            except Exception:  # any exception from a readiness check means not ready (ARC-020, ADR 0040)
                ok = False
            if not ok:
                failing.append(name)
        return JSONResponse({"failing": failing} if failing else {"status": "ready"},
                            status_code=503 if failing else 200)

    router.routes.append(make_metrics_route())  # /metrics is part of the health router (PG-24 D7)
    return router
```

`requestid.py`:

```python
"""X-Request-Id handling (API-004, PG-24)."""
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
        # First x-request-id header; latin-1 never fails to decode (Starlette header encoding, PG-24 D4).
        raw = next((v for k, v in scope["headers"] if k == b"x-request-id"), b"")
        incoming = raw.decode("latin-1")
        rid = incoming if is_ulid(incoming) else new_ulid()
        scope.setdefault("state", {})["request_id"] = rid  # read by the 500 handler (PG-24 D2)
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

**Requirement IDs:** WKL-001, WKL-002, WKL-003, WKL-010, WKL-011, TST-WKL-001, GEN-011, PG-11, PG-12, PG-25, PG-29, LAB-011.
**Depends on:** W1-T02, W1-T08, W1-T16 (`scripts.proc`). **Branch:** `feat/w1-workload-render`.

> **Amended 2026-11-27 after the W1-T09 review, per PG-25 (overview §5; ADR 0044 `wiki/adr/0044-w1-t09-referenced-objects.md`).** The review of `feat/w1-workload-render` at `e5a43f1` ran the Step 3 transform on the real chart output (helm `v3.22.1`, `opentelemetry-demo` `0.42.8`, Step 1 `values.yaml`: 19 Deployments, 18 Services, 3 ConfigMaps, 1 ServiceAccount). The transform kept an object only when its component (label `app.kubernetes.io/component`, else `metadata.name`) is in `KEPT_COMPONENTS`. So it dropped `ServiceAccount/shop` (no component label; `serviceAccountName: shop` in all 19 Deployments, whose pods ServiceAccount admission then rejects) and `ConfigMap/postgresql-init` (no component label; mounted by `astronomy-db`, whose pod then stays `ContainerCreating`). The fixture hid both defects, because its ServiceAccount carried a component label. Changed: "Files" (fixture), "Output", "Interfaces", the Step 2 test block plus the new fixture YAML, the Step 3 and Step 4 blocks, and Step 6 (expected files). The W1-T09 implementer applies them on `feat/w1-workload-render` as a review fix and replaces the "Unverified (2026-11-27): the ServiceAccount name …" paragraph of `wiki/components/workload.md` with the D2 result below.
> - **D1 (keep rule).** An object other than a `Secret` is kept by the first rule that applies. R1: ConfigMap `flagd-config` goes to `flagd-config` (WKL-010 step 6). R2: an object whose component is in `KEPT_COMPONENTS` goes to `<component>` (unchanged). R3: a `ServiceAccount` or `ConfigMap` that a kept workload references. A kept workload is a Deployment or StatefulSet that R2 keeps. Its references are read from `spec.template.spec` after WKL-010 steps 3 to 7 by `pod_references`: `serviceAccountName` (or the deprecated `serviceAccount`), `volumes[].configMap.name`, `volumes[].projected.sources[].configMap.name`, and in `containers[]` and `initContainers[]` `envFrom[].configMapRef.name` and `env[].valueFrom.configMapKeyRef.name`. `pod_references` also reads the Secret references `imagePullSecrets[].name`, `volumes[].secret.secretName`, `volumes[].projected.sources[].secret.name`, `envFrom[].secretRef.name` and `env[].valueFrom.secretKeyRef.name`. Fields that are absent or `null` count as empty. Every other object is dropped, including a `Namespace` (R3 never keeps one). Pseudocode: ADR 0044 D1.
> - **D2 (file placement).** An R3 object referenced by the kept workloads of exactly one component `<c>` goes to `workload/<c>.yaml`. An R3 object referenced by two or more components goes to `workload/serviceaccount.yaml` (ServiceAccount) or `workload/configmaps.yaml` (ConfigMap). The reserved stems `flagd-config`, `serviceaccount`, `configmaps` and `networkpolicies` are not WKL-002 names, and a file is written only when it holds at least one object. Real chart `0.42.8`: exactly 22 files. `ServiceAccount/shop` goes to `workload/serviceaccount.yaml`, `ConfigMap/postgresql-init` to `workload/astronomy-db.yaml`, the labelled `ConfigMap/product-catalog-product-catalog-otel-config` stays in `workload/product-catalog.yaml`, and no `workload/configmaps.yaml` is written (Step 6 list).
> - **D3 (Secrets, Namespace, errors).** Secrets are always removed (WKL-010 step 2), and Namespace handling is unchanged (step 1; kept only by R2). A required reference (no `optional: true`) is unresolved when its object is not in the output and is not ServiceAccount `default` or ConfigMap `kube-root-ca.crt` (`AUTO_CREATED`). Every required Secret reference is unresolved. `transform` then raises `UnresolvedReferenceError` (a `ValueError`; `errors` holds the sorted, de-duplicated messages `unresolved reference <WorkloadKind>/<workload> -> <Kind>/<name> (Secrets are removed by WKL-010 step 2)` for a Secret, or `(not in the helm template output)` for any other kind). `render_workload.py` prints each message as `render_workload: <message>` on stderr and exits `3` before it writes or deletes anything.
> - **D4 (interfaces, fixture).** "Interfaces" and "Output" below list the new names. The fixture MUST contain the real-shape `ServiceAccount/shop` (no component label), referenced by `serviceAccountName: shop` in every fixture Deployment, and `ConfigMap/postgresql-init`, mounted by the kept Deployment `astronomy-db`. It also contains `ConfigMap/shop-shared-env` (shared by `payment` and `load-generator`), `ConfigMap/orphan-config` (unreferenced) and `ConfigMap/jaeger-sampling` (referenced only by the dropped `jaeger`). The exact YAML is in Step 2.
> - **D5 (tests).** New tests `test_referenced_serviceaccount_kept`, `test_referenced_configmap_kept_in_workload_file`, `test_unreferenced_unlabelled_object_dropped` and `test_every_reference_of_kept_workload_resolves` (the output contains every `serviceAccountName` and ConfigMap reference of every kept workload), plus `test_missing_reference_rejected` and `test_secret_reference_rejected` (D3).

> **Amended 2026-11-28 after the W1-T12 bring-up (`feat/w1-task-up`, PR #30), per PG-29 (overview §5; ADR 0048 `wiki/adr/0048-kafka-kraft-voter-localhost.md`).** In the `baseline-v1` render (`rootline-env` `1acc350`) Deployment `kafka` never becomes Ready: the chart voter `KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093` reaches the pod's own KRaft controller through Service `kafka`, which has no endpoint until the pod is Ready, and the WKL-010 step 4 probe (`tcpSocket` 9092) passes only after the broker has registered with that controller. Changed, with the ADR 0048 item in brackets: Requirement IDs; "Files" (fixture line); "Interfaces" (`KAFKA_QUORUM_VOTERS`, `BASELINE_TAG`); Step 2 ("Fixture additions" items 6 and 7, the two kafka tests, the two changed assertions of `test_render_workload_writes_files_and_baseline`; D2); Step 3 (constant and the `kafka` rule; D1); Step 4 (`BASELINE_TAG`; D3); Step 6 (kafka checks); Step 7 (re-renders after `baseline-v1`; D3). W1-T09 is merged, so a W1-T12 fix round on `feat/w1-task-up` applies these changes ("Task W1-T12", amendment note of 2026-11-28); the coordinator then re-renders into `rootline-env` as `baseline-v2` (ADR 0048 D3) and checks the live rollout (D4).
> - **Transform rule (D1, WKL-010 step 7).** Kind `Deployment` or `StatefulSet` whose component is `kafka`; container `spec.template.spec.containers[0]`; env entry `KAFKA_CONTROLLER_QUORUM_VOTERS`; value `1@localhost:9093`, set with `_set_env` (replaced in place when present, appended at the end of `env` when absent). Service `kafka` (no `publishNotReadyAddresses`), `KAFKA_LISTENERS`, `KAFKA_ADVERTISED_LISTENERS` and the step 4 probe stay unchanged. Valid only with one `kafka` replica.
> - **Tests (D2).** `test_kafka_controller_quorum_voter_is_localhost` asserts, on the Step 2 fixture, that `out["kafka"]` holds `Service` then `Deployment`, that container 0 has exactly one `KAFKA_CONTROLLER_QUORUM_VOTERS` entry with value `1@localhost:9093`, that `KAFKA_LISTENERS == "PLAINTEXT://:9092,CONTROLLER://:9093"` and `KAFKA_ADVERTISED_LISTENERS == "PLAINTEXT://kafka:9092"`, that `readinessProbe == {"tcpSocket": {"port": 9092}, "initialDelaySeconds": 5, "periodSeconds": 10, "failureThreshold": 3}`, and that the Service spec has no `publishNotReadyAddresses`. `test_kafka_controller_quorum_voter_added_when_absent` removes the entry from the input and asserts that the last env entry of the output is `{"name": "KAFKA_CONTROLLER_QUORUM_VOTERS", "value": "1@localhost:9093"}`. `test_render_workload_writes_files_and_baseline` expects `kafka.yaml` between `flagd.yaml` and `load-generator.yaml` and `{"baseline_tag": "baseline-v2", "rendered_from": "0.42.8"}`.
> - **Baseline tag (D3).** `scripts/render_workload.py` writes `BASELINE_TAG` (`"baseline-v2"`); each re-render after it raises N by 1 (`baseline-v3` next). `baseline-v1` is never moved or deleted.

**Files:**
- Create: `deploy/upstream/otel-demo/values.yaml`, `scripts/render_workload.py`, `scripts/workload_transforms.py`
- Create: `tests/repo/fixtures/otel-demo-mini.yaml` (hand-written excerpt of `helm template` output; PG-25): ServiceAccount `shop` (real shape, no component label); one `Secret` (`shop-registry-credentials`, label `app.kubernetes.io/component: payment`); ConfigMap `flagd-config` with key `demo.flagd.json` containing two flags, one with `defaultVariant: "on"`; Services `payment`, `flagd` and one Service of a disabled component; Deployments `payment`, `flagd` (with `init-config` initContainer, `flagd-ui` sidecar, `config-rw` emptyDir, `config-ro` volume on ConfigMap `flagd-config`), `load-generator`, `astronomy-db` and `jaeger` (disabled component); ConfigMaps `postgresql-init`, `shop-shared-env`, `orphan-config`, `jaeger-sampling`; Service and Deployment `kafka` (real shape, chart voter `1@kafka:9093`; PG-29). Step 2 "Fixture additions" gives the exact YAML and edits (items 1 to 7). Every Deployment sets `serviceAccountName: shop`.
- Test: `tests/repo/test_workload_render.py`
- Output (in `rootline-env`): `workload/<component>.yaml`, `workload/flagd-config.yaml`, `workload/networkpolicies.yaml`, `workload/serviceaccount.yaml` (ServiceAccounts referenced by two or more components; written only when non-empty), `workload/configmaps.yaml` (unlabelled ConfigMaps referenced by two or more components; written only when non-empty, so not for chart `0.42.8`), `.rootline/baseline.json`

**Interfaces:**
- Produces: `scripts.workload_transforms.transform(docs: list[dict]) -> dict[str, list[dict]]` (file stem → objects; stems are the kept component names, `flagd-config`, `networkpolicies`, and `serviceaccount` / `configmaps` when non-empty; raises `UnresolvedReferenceError` per PG-25 D3); `scripts.workload_transforms.pod_references(spec: dict) -> set[tuple[str, str, bool]]` (`(kind, name, optional)` of every ServiceAccount, ConfigMap and Secret reference of one pod spec, PG-25 D1); `class UnresolvedReferenceError(ValueError)` with attribute `errors: list[str]` (sorted, de-duplicated messages; `str(exc)` joins them with `\n`); `scripts.workload_transforms.dump(objs: list[dict]) -> str`; constants `KEPT_COMPONENTS` (the 19 names of WKL-002), `COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"`, `REFERENCED_KINDS = ("ServiceAccount", "ConfigMap")`, `SHARED_STEMS = {"ServiceAccount": "serviceaccount", "ConfigMap": "configmaps"}`, `AUTO_CREATED = frozenset({("ServiceAccount", "default"), ("ConfigMap", "kube-root-ca.crt")})`, `KAFKA_QUORUM_VOTERS = "1@localhost:9093"` (WKL-010 step 7, PG-29); `scripts.render_workload.BASELINE_TAG = "baseline-v2"` (the `baseline_tag` written into `.rootline/baseline.json`; +1 on every re-render, WKL-001, PG-29).
- CLI: `uv run python scripts/render_workload.py --out <dir>`. Exit `0`: files and `.rootline/baseline.json` written. Exit `3`: one or more unresolved references, one stderr line `render_workload: <message>` each, nothing created, deleted or written. Exit `1` with a Python traceback: `helm` failed (`subprocess.CalledProcessError` from `scripts.proc.run`) or `versions.yaml` could not be loaded.

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
"""Verifies WKL-010, WKL-011 (TST-WKL-001), PG-11, PG-12, PG-25."""
import json
from pathlib import Path

import pytest
import yaml

from scripts.workload_transforms import COLLECTOR_FQDN, UnresolvedReferenceError, dump, transform

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


def where(out: dict[str, list[dict]]) -> dict[tuple[str, str], str]:
    """(kind, name) -> file stem, for every object in the output."""
    return {(o["kind"], o["metadata"]["name"]): stem for stem, objs in out.items() for o in objs}


def test_referenced_serviceaccount_kept() -> None:
    """PG-25 D1, D2: ServiceAccount shop has no component label and is shared -> serviceaccount."""
    out = transform(docs())
    assert where(out)[("ServiceAccount", "shop")] == "serviceaccount"
    assert [(o["kind"], o["metadata"]["name"]) for o in out["serviceaccount"]] == [("ServiceAccount", "shop")]
    assert out["serviceaccount"][0]["metadata"]["namespace"] == "shop"


def test_referenced_configmap_kept_in_workload_file() -> None:
    """PG-25 D1, D2: one referrer -> the workload's file; several -> configmaps."""
    out = transform(docs())
    assert where(out)[("ConfigMap", "postgresql-init")] == "astronomy-db"
    assert [o["kind"] for o in out["astronomy-db"]] == ["ConfigMap", "Deployment"]
    assert where(out)[("ConfigMap", "shop-shared-env")] == "configmaps"
    assert where(out)[("ConfigMap", "flagd-config")] == "flagd-config"


def test_unreferenced_unlabelled_object_dropped() -> None:
    """PG-25 D1: no kept component and no reference from a kept workload -> dropped."""
    found = where(transform(docs()))
    assert ("ConfigMap", "orphan-config") not in found
    assert ("ConfigMap", "jaeger-sampling") not in found  # referenced only by the dropped jaeger Deployment
    assert ("Deployment", "jaeger") not in found


def test_every_reference_of_kept_workload_resolves() -> None:
    """PG-25 D4: every serviceAccountName and ConfigMap reference of every kept workload is in the output."""
    out = transform(docs())
    found = set(where(out))
    wanted: set[tuple[str, str]] = set()
    for o in (o for objs in out.values() for o in objs if o["kind"] in ("Deployment", "StatefulSet")):
        spec = o["spec"]["template"]["spec"]
        if spec.get("serviceAccountName"):
            wanted.add(("ServiceAccount", spec["serviceAccountName"]))
        for v in spec.get("volumes") or []:
            if "configMap" in v:
                wanted.add(("ConfigMap", v["configMap"]["name"]))
        for c in (spec.get("containers") or []) + (spec.get("initContainers") or []):
            for src in c.get("envFrom") or []:
                if "configMapRef" in src:
                    wanted.add(("ConfigMap", src["configMapRef"]["name"]))
            for e in c.get("env") or []:
                if "configMapKeyRef" in (e.get("valueFrom") or {}):
                    wanted.add(("ConfigMap", e["valueFrom"]["configMapKeyRef"]["name"]))
    assert wanted == {("ServiceAccount", "shop"), ("ConfigMap", "flagd-config"),
                      ("ConfigMap", "postgresql-init"), ("ConfigMap", "shop-shared-env")}
    assert wanted <= found


def test_missing_reference_rejected() -> None:
    """PG-25 D3: a required reference that the chart output lacks raises, naming every referrer."""
    ds = [d for d in docs() if (d["kind"], d["metadata"]["name"]) != ("ConfigMap", "postgresql-init")]
    with pytest.raises(UnresolvedReferenceError) as err:
        transform(ds)
    assert err.value.errors == [
        "unresolved reference Deployment/astronomy-db -> ConfigMap/postgresql-init "
        "(not in the helm template output)"
    ]


def test_secret_reference_rejected() -> None:
    """PG-25 D3: Secrets are never kept, so a required Secret reference of a kept workload is an error."""
    ds = docs()
    dep = next(d for d in ds if d["kind"] == "Deployment" and d["metadata"]["name"] == "payment")
    dep["spec"]["template"]["spec"]["containers"][0]["envFrom"].append(
        {"secretRef": {"name": "shop-registry-credentials"}})
    with pytest.raises(UnresolvedReferenceError) as err:
        transform(ds)
    assert err.value.errors == [
        "unresolved reference Deployment/payment -> Secret/shop-registry-credentials "
        "(Secrets are removed by WKL-010 step 2)"
    ]
```

**Fixture additions (PG-25 D4).** Apply these to `tests/repo/fixtures/otel-demo-mini.yaml`, in this order:

1. Delete every `ServiceAccount` document and any existing Deployment `jaeger`. The fixture then holds no ServiceAccount with label `app.kubernetes.io/component`.
2. Append the seven documents below, in the order shown (`---` between documents). They are: ServiceAccount `shop` with exactly the labels of the real render; ConfigMap `postgresql-init`; ConfigMap `shop-shared-env`; ConfigMap `orphan-config`; ConfigMap `jaeger-sampling`; Deployment `astronomy-db`; and Deployment `jaeger`, which replaces the one deleted in item 1.
3. In every Deployment's `spec.template.spec`, set `serviceAccountName: shop` (`astronomy-db` and `jaeger` below already have it).
4. In Deployment `payment`, container `payment` (index 0), set `envFrom: [{configMapRef: {name: shop-shared-env}}]`.
5. In Deployment `load-generator`, container `load-generator` (index 0), append to `env` the entry `{name: SHOP_REGION, valueFrom: {configMapKeyRef: {name: shop-shared-env, key: SHOP_REGION}}}`.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: shop
  labels:
    helm.sh/chart: opentelemetry-demo-0.42.8
    app.kubernetes.io/version: 3.1.0
    app.kubernetes.io/part-of: opentelemetry-demo
    app.kubernetes.io/managed-by: Helm
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgresql-init
  namespace: shop
  labels:
    helm.sh/chart: opentelemetry-demo-0.42.8
    app.kubernetes.io/version: 3.1.0
    app.kubernetes.io/part-of: opentelemetry-demo
    app.kubernetes.io/managed-by: Helm
data:
  init.sql: |
    CREATE TABLE products (id TEXT PRIMARY KEY);
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: shop-shared-env
  namespace: shop
  labels:
    app.kubernetes.io/part-of: opentelemetry-demo
data:
  SHOP_REGION: eu-west-1
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: orphan-config
  namespace: shop
  labels:
    app.kubernetes.io/part-of: opentelemetry-demo
data:
  unused: "true"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: jaeger-sampling
  namespace: shop
  labels:
    app.kubernetes.io/part-of: opentelemetry-demo
data:
  sampling.json: "{}"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: astronomy-db
  namespace: default
  labels:
    app.kubernetes.io/component: astronomy-db
    app.kubernetes.io/name: astronomy-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: astronomy-db
  template:
    metadata:
      labels:
        app.kubernetes.io/component: astronomy-db
        app.kubernetes.io/name: astronomy-db
    spec:
      serviceAccountName: shop
      containers:
        - name: astronomy-db
          image: ghcr.io/open-telemetry/demo:3.1.0-astronomy-db
          ports:
            - containerPort: 5432
              name: postgres
          volumeMounts:
            - name: postgresql-init
              mountPath: /docker-entrypoint-initdb.d
      volumes:
        - name: postgresql-init
          configMap:
            name: postgresql-init
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: default
  labels:
    app.kubernetes.io/component: jaeger
    app.kubernetes.io/name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: jaeger
  template:
    metadata:
      labels:
        app.kubernetes.io/component: jaeger
        app.kubernetes.io/name: jaeger
    spec:
      serviceAccountName: shop
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:1.0
          ports:
            - containerPort: 16686
          volumeMounts:
            - name: sampling
              mountPath: /etc/jaeger
      volumes:
        - name: sampling
          configMap:
            name: jaeger-sampling
```

**Fixture additions (PG-29, ADR 0048 D2).** After items 1 to 5:

6. Append Service `kafka` (first document below) at the end of the file, preceded by a `---` line.
7. Append Deployment `kafka` (second document below) after it, preceded by a `---` line. Both have the real-render shape of chart `0.42.8`, reduced to the fields the transform and the tests read; the env keeps the chart order and the chart voter `1@kafka:9093`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kafka
  namespace: default
  labels:
    app.kubernetes.io/component: kafka
    app.kubernetes.io/name: kafka
spec:
  type: ClusterIP
  ports:
    - port: 9092
      name: plaintext
      targetPort: 9092
    - port: 9093
      name: controller
      targetPort: 9093
  selector:
    opentelemetry.io/name: kafka
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka
  namespace: default
  labels:
    app.kubernetes.io/component: kafka
    app.kubernetes.io/name: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      opentelemetry.io/name: kafka
  template:
    metadata:
      labels:
        opentelemetry.io/name: kafka
        app.kubernetes.io/component: kafka
        app.kubernetes.io/name: kafka
    spec:
      serviceAccountName: shop
      containers:
        - name: kafka
          image: ghcr.io/open-telemetry/demo:3.1.0-kafka
          ports:
            - containerPort: 9092
              name: plaintext
            - containerPort: 9093
              name: controller
          env:
            - name: OTEL_COLLECTOR_NAME
              value: otel-collector
            - name: KAFKA_ADVERTISED_LISTENERS
              value: PLAINTEXT://kafka:9092
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: http://$(OTEL_COLLECTOR_NAME):4318
            - name: KAFKA_LISTENERS
              value: PLAINTEXT://:9092,CONTROLLER://:9093
            - name: KAFKA_CONTROLLER_LISTENER_NAMES
              value: CONTROLLER
            - name: KAFKA_CONTROLLER_QUORUM_VOTERS
              value: 1@kafka:9093
```

**Kafka tests (PG-29, ADR 0048 D2).** Add these two tests to `tests/repo/test_workload_render.py` directly before `def where(`, and set the module docstring to `"""Verifies WKL-010, WKL-011 (TST-WKL-001), PG-11, PG-12, PG-25, PG-29."""`:

```python
def test_kafka_controller_quorum_voter_is_localhost() -> None:
    """WKL-010 step 7, PG-29 (ADR 0048): the KRaft voter is the kafka pod itself, not Service kafka."""
    out = transform(docs())
    assert [o["kind"] for o in out["kafka"]] == ["Service", "Deployment"]
    dep = next(o for o in out["kafka"] if o["kind"] == "Deployment")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    names = [e["name"] for e in container["env"]]
    env = {e["name"]: e.get("value") for e in container["env"]}
    assert names.count("KAFKA_CONTROLLER_QUORUM_VOTERS") == 1
    assert env["KAFKA_CONTROLLER_QUORUM_VOTERS"] == "1@localhost:9093"
    assert env["KAFKA_LISTENERS"] == "PLAINTEXT://:9092,CONTROLLER://:9093"
    assert env["KAFKA_ADVERTISED_LISTENERS"] == "PLAINTEXT://kafka:9092"
    assert container["readinessProbe"] == {
        "tcpSocket": {"port": 9092},
        "initialDelaySeconds": 5,
        "periodSeconds": 10,
        "failureThreshold": 3,
    }
    svc = next(o for o in out["kafka"] if o["kind"] == "Service")
    assert "publishNotReadyAddresses" not in svc["spec"]


def test_kafka_controller_quorum_voter_added_when_absent() -> None:
    """WKL-010 step 7, PG-29 (ADR 0048): a chart output without the variable gets it appended."""
    ds = docs()
    dep = next(d for d in ds if d["kind"] == "Deployment" and d["metadata"]["name"] == "kafka")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    container["env"] = [e for e in container["env"] if e["name"] != "KAFKA_CONTROLLER_QUORUM_VOTERS"]
    out = next(o for o in transform(ds)["kafka"] if o["kind"] == "Deployment")
    env = out["spec"]["template"]["spec"]["containers"][0]["env"]
    assert env[-1] == {"name": "KAFKA_CONTROLLER_QUORUM_VOTERS", "value": "1@localhost:9093"}
```

In the existing `test_render_workload_writes_files_and_baseline`, the expected file list gains `"kafka.yaml"` between `"flagd.yaml"` and `"load-generator.yaml"` (nine names), and the baseline assertion is `assert baseline == {"baseline_tag": "baseline-v2", "rendered_from": "0.42.8"}`. No other test changes: `test_every_reference_of_kept_workload_resolves` keeps its four expected references, because the fixture `kafka` references only `ServiceAccount/shop`. Red check (planner, 2026-11-28, on `develop` `3a299a0` with the fixture and tests applied and Steps 3 and 4 not yet amended): `3 failed, 23 passed`, the failures being the two kafka tests and `test_render_workload_writes_files_and_baseline`; with the PG-29 Step 3 and Step 4 changes: `26 passed`.

Run: `uv run pytest tests/repo/test_workload_render.py -v` → FAIL. On `e5a43f1`, collection fails with `ImportError` (no `UnresolvedReferenceError`). Five tests need the Step 3 keep rule and fail even when the import is satisfied: `test_referenced_serviceaccount_kept`, `test_referenced_configmap_kept_in_workload_file`, `test_every_reference_of_kept_workload_resolves`, `test_missing_reference_rejected` and `test_secret_reference_rejected` (planner check, 2026-11-27). `test_unreferenced_unlabelled_object_dropped` already passes on the old rule and guards against regressions.

- [ ] **Step 3: Implement `scripts/workload_transforms.py`**

```python
"""Pure transforms for rendered OTel Demo manifests (WKL-010, PG-11, PG-12, PG-25, PG-29)."""
from __future__ import annotations

import copy
import json
from typing import Any

import yaml

COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"
# WKL-010 step 7, PG-29 (ADR 0048 D1): the single KRaft voter is the kafka pod itself, not Service kafka.
KAFKA_QUORUM_VOTERS = "1@localhost:9093"
KEPT_COMPONENTS = [
    "frontend", "frontend-proxy", "load-generator", "flagd", "ad", "cart", "valkey-cart", "checkout",
    "currency", "email", "payment", "product-catalog", "astronomy-db", "quote", "recommendation",
    "shipping", "kafka", "fraud-detection", "image-provider",
]
WORKLOAD_KINDS = ("Deployment", "StatefulSet")
KIND_ORDER = ["ServiceAccount", "ConfigMap", "Service", "Deployment", "StatefulSet"]
# Kinds that the reference rule can keep, and the shared file of each (PG-25 D1, D2).
REFERENCED_KINDS = ("ServiceAccount", "ConfigMap")
SHARED_STEMS = {"ServiceAccount": "serviceaccount", "ConfigMap": "configmaps"}
# Objects Kubernetes creates in every namespace; a reference to one is never an error (PG-25 D3).
AUTO_CREATED = frozenset({("ServiceAccount", "default"), ("ConfigMap", "kube-root-ca.crt")})


class UnresolvedReferenceError(ValueError):
    """A kept workload references an object that is not in the output (PG-25 D3)."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def component_of(obj: dict[str, Any]) -> str:
    labels = obj.get("metadata", {}).get("labels", {}) or {}
    return labels.get("app.kubernetes.io/component") or obj["metadata"]["name"]


def pod_references(spec: dict[str, Any]) -> set[tuple[str, str, bool]]:
    """(kind, name, optional) of every object a pod spec references by name (PG-25 D1)."""
    refs: set[tuple[str, str, bool]] = set()
    account = spec.get("serviceAccountName") or spec.get("serviceAccount")
    if account:
        refs.add(("ServiceAccount", account, False))
    for pull in spec.get("imagePullSecrets") or []:
        refs.add(("Secret", pull["name"], False))
    for vol in spec.get("volumes") or []:
        if "configMap" in vol:
            refs.add(("ConfigMap", vol["configMap"]["name"], bool(vol["configMap"].get("optional"))))
        if "secret" in vol:
            refs.add(("Secret", vol["secret"]["secretName"], bool(vol["secret"].get("optional"))))
        for src in (vol.get("projected") or {}).get("sources") or []:
            if "configMap" in src:
                refs.add(("ConfigMap", src["configMap"]["name"], bool(src["configMap"].get("optional"))))
            if "secret" in src:
                refs.add(("Secret", src["secret"]["name"], bool(src["secret"].get("optional"))))
    for c in (spec.get("containers") or []) + (spec.get("initContainers") or []):
        for src in c.get("envFrom") or []:
            if "configMapRef" in src:
                refs.add(("ConfigMap", src["configMapRef"]["name"], bool(src["configMapRef"].get("optional"))))
            if "secretRef" in src:
                refs.add(("Secret", src["secretRef"]["name"], bool(src["secretRef"].get("optional"))))
        for e in c.get("env") or []:
            value_from = e.get("valueFrom") or {}
            if "configMapKeyRef" in value_from:
                ref = value_from["configMapKeyRef"]
                refs.add(("ConfigMap", ref["name"], bool(ref.get("optional"))))
            if "secretKeyRef" in value_from:
                ref = value_from["secretKeyRef"]
                refs.add(("Secret", ref["name"], bool(ref.get("optional"))))
    return refs


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
    placed: set[tuple[str, str]] = set()  # (kind, name) of every object already in `out`
    candidates: dict[tuple[str, str], dict[str, Any]] = {}  # unplaced ServiceAccounts and ConfigMaps
    # (kind, name) -> {(component, workload kind, workload name)} of the kept workloads referencing it
    referrers: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    required: set[tuple[str, str]] = set()  # referenced at least once without optional: true
    for original in docs:
        obj = copy.deepcopy(original)
        if obj["kind"] == "Secret":
            continue
        obj["metadata"]["namespace"] = "shop"
        obj["metadata"].pop("managedFields", None)
        key = (obj["kind"], obj["metadata"]["name"])
        if obj["kind"] == "ConfigMap" and obj["metadata"]["name"] == "flagd-config":
            _flags_off(obj)
            out.setdefault("flagd-config", []).append(obj)
            placed.add(key)
            continue
        comp = component_of(obj)
        if comp not in KEPT_COMPONENTS:
            if obj["kind"] in REFERENCED_KINDS:
                candidates[key] = obj
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
            if comp == "kafka":  # WKL-010 step 7, PG-29 (ADR 0048 D1)
                _set_env(spec["containers"][0], "KAFKA_CONTROLLER_QUORUM_VOTERS", KAFKA_QUORUM_VOTERS)
            for kind, name, optional in pod_references(spec):
                referrers.setdefault((kind, name), set()).add((comp, obj["kind"], obj["metadata"]["name"]))
                if not optional:
                    required.add((kind, name))
        out.setdefault(comp, []).append(obj)
        placed.add(key)
    errors: set[str] = set()
    for key in sorted(referrers):
        kind, name = key
        if key in placed or key in AUTO_CREATED:
            continue
        if kind in REFERENCED_KINDS and key in candidates:
            comps = sorted({comp for comp, _, _ in referrers[key]})
            stem = comps[0] if len(comps) == 1 else SHARED_STEMS[kind]
            out.setdefault(stem, []).append(candidates[key])
            placed.add(key)
            continue
        if key not in required:
            continue
        reason = "Secrets are removed by WKL-010 step 2" if kind == "Secret" else "not in the helm template output"
        for _, wkind, wname in referrers[key]:
            errors.add(f"unresolved reference {wkind}/{wname} -> {kind}/{name} ({reason})")
    if errors:
        raise UnresolvedReferenceError(sorted(errors))
    for objs in out.values():
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
Exit codes: 0 written; 3 a kept workload references an object missing from the output (PG-25 D3),
nothing written. A failing helm command raises subprocess.CalledProcessError (exit 1).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run
from scripts.versions_lib import REPO, load_versions
from scripts.workload_transforms import UnresolvedReferenceError, dump, transform

# WKL-001, GEN-011, PG-29 (ADR 0048 D3): the rootline-env tag of this render; +1 on every re-render.
BASELINE_TAG = "baseline-v2"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    demo = load_versions()["opentelemetry-demo"]
    run(["helm", "repo", "add", "open-telemetry", demo["repo"], "--force-update"])
    rendered = run(["helm", "template", "shop", "open-telemetry/opentelemetry-demo", "--version",
                    demo["chart"], "--namespace", "shop", "-f",
                    str(REPO / "deploy/upstream/otel-demo/values.yaml")]).stdout
    try:
        files = transform([d for d in yaml.safe_load_all(rendered) if d])
    except UnresolvedReferenceError as exc:  # PG-25 D3: report every error, write nothing
        for line in exc.errors:
            print(f"render_workload: {line}", file=sys.stderr)
        return 3
    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.yaml"):
        stale.unlink()
    for stem, objs in sorted(files.items()):
        (args.out / f"{stem}.yaml").write_text(dump(objs), encoding="utf-8", newline="\n")
    meta = args.out.parent / ".rootline/baseline.json"
    meta.parent.mkdir(exist_ok=True)
    meta.write_text(json.dumps({"baseline_tag": BASELINE_TAG, "rendered_from": demo["chart"]},
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
ls "$ROOTLINE_ENV_DIR/workload"
grep -c '^kind: ServiceAccount$' "$ROOTLINE_ENV_DIR/workload/serviceaccount.yaml"
grep '^kind:' "$ROOTLINE_ENV_DIR/workload/astronomy-db.yaml"
grep -c 'value: 1@localhost:9093' "$ROOTLINE_ENV_DIR/workload/kafka.yaml"
grep -c 'value: 1@kafka:9093' "$ROOTLINE_ENV_DIR/workload/kafka.yaml"
```

Expected (PG-25 D2; planner run on 2026-11-27 with chart `0.42.8`). Both renders exit `0`. `ls` prints exactly these 22 names: `ad.yaml`, `astronomy-db.yaml`, `cart.yaml`, `checkout.yaml`, `currency.yaml`, `email.yaml`, `flagd-config.yaml`, `flagd.yaml`, `fraud-detection.yaml`, `frontend-proxy.yaml`, `frontend.yaml`, `image-provider.yaml`, `kafka.yaml`, `load-generator.yaml`, `networkpolicies.yaml`, `payment.yaml`, `product-catalog.yaml`, `quote.yaml`, `recommendation.yaml`, `serviceaccount.yaml`, `shipping.yaml`, `valkey-cart.yaml`; there is no `configmaps.yaml`. The `grep -c` prints `1`. The `grep '^kind:'` prints `kind: ConfigMap`, `kind: Service`, `kind: Deployment`, in that order. The two kafka checks (PG-29, run after the ADR 0048 change; the `baseline-v1` render of 2026-11-27 predates them) print `1` and `0` (the second `grep` exits 1; that is expected). If the render exits `3`, or any of these differs, stop and report `STATUS: BLOCKED` with the stderr lines and the `ls` output. Do not change the transform to match the output.

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

This direct push applies only to the first render (`baseline-v1`, done 2026-11-27 as `1acc350`). Every re-render goes through a `rootline-env` PR, is squash-merged, and gets the tag `BASELINE_TAG` of `scripts/render_workload.py` (spec WKL-001 "Re-rendering"); the `baseline-v2` re-render follows the exact commands of ADR 0048 D3 (PG-29).

---

### Task W1-T10: k3d cluster config and the ArgoCD app-of-apps

**Requirement IDs:** INF-020, INF-021, INF-022 (helpers stub), INF-030, INF-031, ARC-010, ARC-002, GEN-012, SEC-011 (local CoreDNS), SEC-100 (bootstrap store), PG-9, PG-10, PG-22, PG-27.
**Depends on:** W1-T02, W1-T09. **Branch:** `feat/w1-gitops-root`.

> **Amended 2026-11-27, per PG-22 (overview §5; ADR 0041).** Step 5 row `ca-configmap.yaml`: the `copy-ca` Job image is `docker.io/rancher/kubectl` (no shell), so the Job runs `kubectl apply -k` over a projected volume, and the `cert-manager` Role on secret `rootline-local-ca` is dropped.

> **Amended 2026-11-27 after the W1-T10 review of `feat/w1-gitops-root` at `2bc66d5`, per PG-27 (overview §5; ADR 0046 `wiki/adr/0046-w1-t10-t11-review-decisions.md`).** Changed, with the ADR 0046 item in brackets: the root values block (`prometheus-crds` uses `versionKey: prometheus-operator-crds`, no overrides; T1); Step 1 (the added required tests); Step 2 (`gateway.enabled: false`, `ports.websecure.http.tls.enabled`, T9; `.gitignore` belongs to W1-T12, T6); Step 3 (`upstream` values path from `versionKey` and `required`, T2; `gateway-api` `targetRevision: v{{ $v }}`, T3); Step 4 (`observability` PSS `privileged` with `warn`/`audit` `baseline`, O3 item 1); Step 5 rows `gateway.yaml` (listener ports 8000 and 8443, T9), `ca-configmap.yaml` (local/ci only, T5; image from the generated `files/versions.yaml`, T11) and `generators.yaml` (four namespaces, T4); Step 6 (`tpl` in `rootline.image`, T10; no CPU values, T7); Step 8 (`--allow-missing` until W1-P3 integration step 3, T8). The items that depend on W1-T11 (T1 step 3, T8 item 3, T11 item 2) are applied only in "W1-P3 integration steps" step 3 under "Execution schedule" above; all others in the normal fix round.

> **Amended 2026-11-27 after the W1-T12 bring-up (`feat/w1-task-up`, PR #30), per PG-28 (overview §5; ADR 0047 `wiki/adr/0047-w1-t12-bringup-decisions.md`).** Changed, with the ADR 0047 item in brackets: the root values block (every entry has an explicit `namespace`, D1); Step 3 `apps.yaml` (destination line with `required` and no default, D1; `syncPolicy.retry` on every Application, D2). W1-T10 is already merged; W1-T12 applies these changes to `deploy/root/values.yaml`, `deploy/root/templates/apps.yaml` and `tests/repo/test_root_chart.py` in its fix round ("Task W1-T12" Step 2b).

**Files:**
- Create: `infra/k3d/rootline.yaml`, `infra/k3d/manifests/traefik-config.yaml`
- Create: `deploy/root/Chart.yaml`, `deploy/root/values.yaml`, `deploy/root/templates/_app.tpl`, `deploy/root/templates/apps.yaml`
- Create: `deploy/charts/namespaces/{Chart.yaml,values.yaml,templates/namespaces.yaml}`
- Create: `deploy/charts/platform-config/{Chart.yaml,values.yaml,templates/*.yaml}` (cluster issuers and CA, ESO stores and generators, `coredns-custom`, Gateway, `rootline-ca` ConfigMap; Kyverno policies are added in W3-T12), and `deploy/charts/platform-config/files/versions.yaml` (generated by `scripts/render_versions.py`, committed in W1-P3 integration step 3; ADR 0046 T11)
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
apps:                           # every Application; later tasks flip enabled: true; `namespace` is required (PG-28)
  namespaces:        {enabled: true,  wave: -4, kind: local-chart, path: deploy/charts/namespaces, namespace: argocd}
  gateway-api-crds:  {enabled: true,  wave: -4, kind: url, versionKey: gateway-api, namespace: argocd}
  cert-manager:      {enabled: true,  wave: -3, kind: upstream, versionKey: cert-manager, chart: cert-manager, namespace: cert-manager}
  external-secrets:  {enabled: true,  wave: -3, kind: upstream, versionKey: external-secrets, chart: external-secrets, namespace: external-secrets}
  cnpg-operator:     {enabled: true,  wave: -3, kind: upstream, versionKey: cloudnative-pg, chart: cloudnative-pg, namespace: cnpg-system}
  kyverno:           {enabled: true,  wave: -3, kind: upstream, versionKey: kyverno, chart: kyverno, namespace: kyverno}
  chaos-mesh:        {enabled: true,  wave: -3, kind: upstream, versionKey: chaos-mesh, chart: chaos-mesh, namespace: chaos-mesh, envs: [local]}
  prometheus-crds:   {enabled: true,  wave: -3, kind: upstream, versionKey: prometheus-operator-crds, chart: prometheus-operator-crds, namespace: observability}
  traefik:           {enabled: true,  wave: -3, kind: upstream, versionKey: traefik, chart: traefik, namespace: traefik, envs: [gke]}
  platform-config:   {enabled: true,  wave: -2, kind: local-chart, path: deploy/charts/platform-config, namespace: argocd}
  postgres:          {enabled: true,  wave: -1, kind: local-chart, path: deploy/charts/postgres, namespace: rootline-data}
  observability:     {enabled: true,  wave: -1, kind: local-chart, path: deploy/charts/observability, namespace: observability}
  keycloak:          {enabled: false, wave: 0,  kind: local-chart, path: deploy/charts/keycloak, namespace: keycloak}
  argocd-accounts:   {enabled: false, wave: 0,  kind: local-chart, path: deploy/charts/argocd-accounts, namespace: argocd}
  rootline:          {enabled: true,  wave: 1,  kind: local-chart, path: deploy/charts/rootline, namespace: rootline}
  workload:          {enabled: true,  wave: 2,  kind: env-repo, path: workload, namespace: shop}
  demo-seed:         {enabled: false, wave: 2,  kind: local-chart, path: deploy/charts/demo-seed, namespace: rootline, envs: [gke]}
```

Every entry has a `namespace` key, which becomes `spec.destination.namespace`; `apps.yaml` has no default (spec INF-020, PG-28, ADR 0047 D1). The value is the namespace that receives the chart's namespaced objects that do not set `metadata.namespace`; it is `argocd` when every namespaced object of the chart sets its namespace or the chart has only cluster-scoped objects (`namespaces`, `gateway-api-crds`, `platform-config`, `argocd-accounts`).

(`prometheus-crds` uses chart `prometheus-community/prometheus-operator-crds`; its `versions.yaml` key `prometheus-operator-crds` was resolved by W1-T02 and reaches `deploy/root/files/versions.yaml` when W1-T11 adds it to `CHART_KEYS` of `scripts/render_versions.py` (ADR 0046 T1). Until W1-P3 integration step 3, `feat/w1-gitops-root` carries the temporary overrides `repo: https://prometheus-community.github.io/helm-charts` and `chartVersion: "33.0.2"` on this entry; step 3 removes them, and no other entry may carry `repo` or `chartVersion`. `observability` is a local wrapper chart with upstream dependencies, created in W1-T11.)

- Every local chart receives Helm parameters `global.env`, `global.domain`, `global.gcpProject`, `global.k8sIssuer`, `global.artifactsBucket`, `global.ingressIP` and its `values-<env>.yaml` file (`valueFiles: [values.yaml, values-<env>.yaml]`, `ignoreMissingValueFiles: true`).

- [ ] **Step 1: Write the failing tests**

```python
"""Verifies INF-020, INF-021, GEN-012, ARC-010."""
from pathlib import Path

import pytest
import yaml

from scripts.proc import run

REPO = Path(__file__).resolve().parents[2]


def render(env: str) -> list[dict]:
    out = run(["helm", "template", "root", str(REPO / "deploy/root"), "--set", f"env={env}"]).stdout
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
    out = run(["helm", "template", "ns", str(REPO / "deploy/charts/namespaces")]).stdout
    ns = {d["metadata"]["name"]: d["metadata"]["labels"] for d in yaml.safe_load_all(out) if d}
    expected = {"rootline": "restricted", "rootline-data": "restricted", "rootline-lab": "restricted",
                "rootline-secrets": "restricted", "keycloak": "restricted", "observability": "privileged",
                "shop": "baseline", "argocd": "baseline", "chaos-mesh": "privileged", "kyverno": "baseline",
                "external-secrets": "baseline", "cert-manager": "baseline", "cnpg-system": "baseline",
                "traefik": "baseline"}
    for name, level in expected.items():
        assert ns[name]["pod-security.kubernetes.io/enforce"] == level, name
```

Run: `uv run pytest tests/repo/test_root_chart.py -v` → FAIL.

Required test expectations added by PG-27 (ADR 0046); each test's docstring cites the ADR item and the requirement ID in brackets:

| Test | Expectation |
|---|---|
| `test_namespaces_pss` | `expected["observability"] == "privileged"` (O3 item 1, ARC-010); `observability` also has `pod-security.kubernetes.io/warn: baseline`, `pod-security.kubernetes.io/warn-version: latest`, `pod-security.kubernetes.io/audit: baseline`, `pod-security.kubernetes.io/audit-version: latest`; no other namespace has a `warn` or `audit` label |
| `test_application_sources` | Application `prometheus-crds`: `sources[0]` `chart == "prometheus-operator-crds"`, `repoURL` and `targetRevision` equal `repo` and `chart` of `deploy/root/files/versions.yaml` key `prometheus-operator-crds`; every `upstream` Application's first `valueFiles` entry is `$values/deploy/upstream/<versionKey>/values-<env>.yaml` (`cnpg-operator` → `deploy/upstream/cloudnative-pg/`) (T1, T2, INF-020); `gateway-api-crds` `targetRevision == "v" + versions["gateway-api"]` (T3) |
| `test_apps_contract_matches_plan` | no entry of `apps` in `deploy/root/values.yaml` has a `repo` or `chartVersion` key (T1). Until W1-P3 integration step 3 the test allows exactly the two keys on `prometheus-crds`; step 3 removes that allowance |
| `test_traefik_helmchartconfig` | parsed `valuesContent` == `{"deployment": {"replicas": 1}, "gateway": {"enabled": False}, "providers": {"kubernetesGateway": {"enabled": True}}, "ports": {"websecure": {"http": {"tls": {"enabled": True}}}}}` (T9, INF-030) |
| `test_platform_config_tls_and_dns` | `listeners["http"]["port"] == 8000`, `listeners["https"]["port"] == 8443`, protocols `HTTP` and `HTTPS` (T9) |
| `test_platform_config_gke_differences` | on `gke` no `Job/copy-ca`, no `ConfigMap/copy-ca-kustomization`, no ConfigMap `rootline-ca` (T5, SEC-011) |
| `test_eso_stores_and_generators` | `Password/password-48` and `Password/password-43` exist in exactly the namespaces `rootline-data`, `rootline`, `keycloak`, `observability` (T4, SEC-100) |
| `test_copy_ca_image_matches_versions_yaml` | from W1-P3 integration step 3: `yaml.safe_load` of `deploy/charts/platform-config/files/versions.yaml` == `{"kubectl-image": <versions.yaml row>}` and container `copy-ca` image == `<repo>:v<version>@<digest>` of that row; before step 3 it compares `copyCa.image` of `values.yaml` instead (T11, GEN-050) |
| `test_render_manifests_script` | runs `scripts/render_manifests.py` with `--allow-missing` until W1-P3 integration step 3, without arguments after it; exit 0 (T8) |

- [ ] **Step 2: Write `infra/k3d/rootline.yaml` and Traefik config** — exactly INF-030, with the two placeholders kept literally in the committed file: `image: rancher/k3s:<versions.k3s>` and `<repo>` in the volume. `scripts/up.py` (W1-T12) substitutes them at runtime (`<versions.k3s>` = `versions.yaml` `k3s` with `+` replaced by `-`) and writes `infra/k3d/rootline.generated.yaml`; W1-T12 adds that path to `.gitignore` (ADR 0046 T6), and W1-T10 does not edit `.gitignore`. Traefik config:

```yaml
# infra/k3d/manifests/traefik-config.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata: {name: traefik, namespace: kube-system}
spec:
  valuesContent: |-
    deployment:
      replicas: 1
    gateway:
      enabled: false
    providers:
      kubernetesGateway:
        enabled: true
    ports:
      websecure:
        http:
          tls:
            enabled: true
```

k3s `v1.36.6+k3s1` installs Traefik from its bundled chart `traefik-40.1.7+up40.1.0` (Rancher repack of upstream `40.1.0`). `gateway.enabled: false` removes the chart's default Gateway `traefik-gateway`; GatewayClass `traefik` is still created. `ports.websecure.http.tls.enabled` is the chart key for TLS on entry point `websecure` (`ports.websecure.tls` is rejected by the upstream chart schema). Entry points: `web` `:8000`, `websecure` `:8443`; Service `traefik` maps port 80 → 8000 and 443 → 8443 (ADR 0046 T9, verified with `helm template` on 2026-11-27).

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
    namespace: {{ required (printf "deploy/root/values.yaml apps.%s has no namespace" $name) $app.namespace }}
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
  {{- $v := required (printf "deploy/root/files/versions.yaml has no key %s" $app.versionKey) (index $versions $app.versionKey) }}
  sources:
    - repoURL: {{ $v.repo }}
      chart: {{ $app.chart }}
      targetRevision: {{ $v.chart | quote }}
      helm:
        valueFiles:
          - $values/deploy/upstream/{{ $app.versionKey }}/values-{{ $.Values.env }}.yaml
        ignoreMissingValueFiles: true
    - repoURL: {{ $.Values.repoURL }}
      targetRevision: {{ $.Values.targetRevision }}
      ref: values
  {{- else if eq $app.kind "url" }}
  {{- $v := index $versions $app.versionKey }}
  source:
    repoURL: https://github.com/kubernetes-sigs/gateway-api
    targetRevision: v{{ $v }}
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
    retry:
      limit: 10
      backoff: {duration: 10s, factor: 2, maxDuration: 3m}
{{- end }}
{{- end }}
```

Destination and retry (PG-28, ADR 0047 D1 and D2): a missing `namespace` makes `helm template deploy/root` fail with `deploy/root/values.yaml apps.<name> has no namespace`. Every Application, `workload` included, gets `syncPolicy.retry` with delays 10, 20, 40, 80, 160 s, then 180 s five times (1210 s in total, longer than the 1200 s `scripts/wait_apps.py` waits in W1-T12 Step 3 item 7); the same object is `scripts.up.SYNC_RETRY` (W1-T12), and `tests/repo/test_root_chart.py` compares the two. A retry repeats a failed sync of the target revision and does not revert live drift, so `workload` keeps GEN-012.

Values path and versions (ADR 0046 T2, T3): an `upstream` Application reads `$values/deploy/upstream/<versionKey>/values-<env>.yaml`, so `cnpg-operator` reads `deploy/upstream/cloudnative-pg/` and `prometheus-crds` reads `deploy/upstream/prometheus-operator-crds/` (no file; `ignoreMissingValueFiles: true`). `required` makes `helm template` fail with `deploy/root/files/versions.yaml has no key <key>` when the key is missing. `gateway-api` is a scalar in `versions.yaml` (`"1.7.0"`), and the Git tag is `v1.7.0`. On `feat/w1-gitops-root`, until W1-P3 integration step 3, the `upstream` branch keeps `index $versions $app.versionKey | default dict`, `{{ $app.repo | default $v.repo }}` and `{{ $app.chartVersion | default $v.chart | quote }}` for the `prometheus-crds` overrides (ADR 0046 T1); step 3 replaces them with the block above.

The AppProject `rootline-workload` (SEC-110) is created by the `argocd-accounts` chart in W2-T08. Until that app is enabled, the `workload` Application uses project `default` (the `project:` line above implements this).

If the container index from W1-T09 step 6(c) is not 0, change the `jsonPointers` value and the test.

- [ ] **Step 4: Write `deploy/charts/namespaces`** — one `Namespace` per row of ARC-010 plus `cnpg-system` and `traefik`, each with labels `pod-security.kubernetes.io/enforce: <level>`, `pod-security.kubernetes.io/enforce-version: latest`, `rootline.dev/managed: "true"`. `observability` is `privileged` and additionally carries `pod-security.kubernetes.io/warn: baseline`, `pod-security.kubernetes.io/warn-version: latest`, `pod-security.kubernetes.io/audit: baseline`, `pod-security.kubernetes.io/audit-version: latest` (values entry `{name: observability, pss: privileged, warn: baseline, audit: baseline, defaultDeny: true}`; the template renders the `warn` and `audit` pairs only for entries that set those keys; ADR 0046 O3 item 1, owner confirmation in "W1-P3 integration steps" step 5). Default-deny NetworkPolicies for the namespaces marked "yes" in ARC-010 (`rootline`, `rootline-data`, `rootline-lab`, `rootline-secrets`, `keycloak`, `observability`): `podSelector: {}`, `policyTypes: [Ingress, Egress]`, plus an `allow-dns` egress policy to `kube-system` port 53 UDP/TCP. Allow-rules for each flow are added by the charts that own the pods (W1-T11 for observability and postgres, W3-T12 for `rootline`, W3-T01 for keycloak). Exception for week 1: `observability` and `rootline-data` get their allow-rules in W1-T11.

- [ ] **Step 5: Write `deploy/charts/platform-config`**

Templates (each gated by `.Values.global.env` where noted):

| File | Objects |
|---|---|
| `ca.yaml` | (local, ci) `ClusterIssuer selfsigned` (`selfSigned: {}`); `Certificate rootline-local-ca` in `cert-manager` (`isCA: true`, `duration: 87600h`, `privateKey: {algorithm: ECDSA, size: 256}`, `secretName: rootline-local-ca`, `issuerRef: selfsigned`); `ClusterIssuer rootline-ca` (`ca.secretName: rootline-local-ca`); `Certificate rootline-wildcard` in `kube-system` for `*.{{ .Values.global.domain }}` and `{{ .Values.global.domain }}` from `rootline-ca`, secret `rootline-wildcard-tls` |
| `gateway.yaml` | `Gateway rootline` in `kube-system` (local/ci; `traefik` ns on gke), `gatewayClassName: traefik`, listeners `http` (`port: 8000`, `protocol: HTTP`, `allowedRoutes.namespaces.from: All`) and `https` (`port: 8443`, `protocol: HTTPS`, TLS `mode: Terminate` with `certificateRefs: [{name: rootline-wildcard-tls}]`, `allowedRoutes.namespaces.from: All`). The listener port is the Traefik entry point port (`web` 8000, `websecure` 8443); clients still connect to 80 and 443, which Service `traefik` maps to 8000 and 8443 (ADR 0046 T9). An HTTPRoute `parentRefs` entry that names a port uses 8000 or 8443 |
| `coredns.yaml` | (local, ci) `ConfigMap coredns-custom` in `kube-system` with key `rootline.override`: `rewrite name auth.{{D}} traefik.kube-system.svc.cluster.local` and the same for `console.{{D}}` and `argocd.{{D}}` |
| `ca-configmap.yaml` | (local, ci; on gke W7-T02 Step 3 adds ConfigMap `rootline-ca` with the Let's Encrypt roots, ADR 0046 T5) `ConfigMap rootline-ca` in `rootline` and `keycloak` with key `ca.crt`. trust-manager is not installed, so an ArgoCD PostSync Job `copy-ca` in `cert-manager` (annotations `argocd.argoproj.io/hook: PostSync`, `argocd.argoproj.io/hook-delete-policy: BeforeHookCreation`; `backoffLimit: 6`, `activeDeadlineSeconds: 600`) writes the ConfigMap into both namespaces. Image: `versions.yaml` key `kubectl-image` as `<repo>:v<version>@<digest>`, read by the template from the generated file `deploy/charts/platform-config/files/versions.yaml` (`{{- $kubectl := index (.Files.Get "files/versions.yaml" | fromYaml) "kubectl-image" }}`, `image: {{ printf "%s:v%s@%s" $kubectl.repo $kubectl.version $kubectl.digest }}`; there is no `copyCa.image` value; ADR 0046 T11; until W1-P3 integration step 3 `feat/w1-gitops-root` keeps `copyCa.image` in `values.yaml`), which on 2026-11-27 is `docker.io/rancher/kubectl:v1.36.2@sha256:06c7a7a9772737494ae1e0c3af90f1b5385630c147e47c1c7cea92f4bed55fbe` (PG-22, ADR 0041; the image holds only `/bin/kubectl`, no shell, user `kubectl` UID 1000). Because there is no shell, the Job runs one `kubectl` command and gets the CA through a volume, not through the API: ConfigMap `copy-ca-kustomization` in `cert-manager` holds key `kustomization.yaml` with exactly `apiVersion: kustomize.config.k8s.io/v1beta1`, `kind: Kustomization`, `generatorOptions: {disableNameSuffixHash: true}`, `configMapGenerator: [{name: rootline-ca, namespace: rootline, files: [ca.crt]}, {name: rootline-ca, namespace: keycloak, files: [ca.crt]}]`; the pod mounts one `projected` volume `work` at `/work` (read-only) with sources configMap `copy-ca-kustomization` (item `kustomization.yaml`) and secret `rootline-local-ca` (item `ca.crt` → path `ca.crt`), plus an `emptyDir` volume `tmp` at `/tmp`. Container `copy-ca`: `command: ["/bin/kubectl", "apply", "-k", "/work"]`, env `HOME=/tmp` (kubectl's discovery cache), securityContext `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities: {drop: [ALL]}`, `seccompProfile: {type: RuntimeDefault}`; `restartPolicy: Never`. If secret `rootline-local-ca` does not exist yet, the kubelet keeps the pod in `ContainerCreating` and retries the mount until it appears or `activeDeadlineSeconds` ends the Job (the PostSync hook then fails and the next sync runs it again). RBAC: ServiceAccount `copy-ca` in `cert-manager` (no Role in `cert-manager`: the kubelet, not the ServiceAccount, reads the secret for the volume); Roles in `rootline` and `keycloak` with `get,create,patch` on configmaps (`resourceNames: [rootline-ca]` for `get,patch`; `create` cannot be restricted by name), each bound to ServiceAccount `cert-manager/copy-ca`. Verified on 2026-11-27: `kubectl kustomize` of this kustomization in `docker.io/rancher/kubectl:v1.36.2`, run as UID 1000 with a read-only root filesystem over a directory with the projected-volume symlink layout, prints the two ConfigMaps |
| `eso-bootstrap.yaml` | (local, ci) ServiceAccount `eso-bootstrap-reader` in `rootline-secrets`; Role `get,list,watch` on secrets named `rootline-bootstrap`; `ClusterSecretStore bootstrap` (`provider.kubernetes.remoteNamespace: rootline-secrets`, `auth.serviceAccount: {name: eso-bootstrap-reader, namespace: rootline-secrets}`, `server.caProvider: {type: ConfigMap, name: kube-root-ca.crt, key: ca.crt, namespace: rootline-secrets}`) |
| `eso-pg-roles.yaml` | ServiceAccount `eso-pg-reader` in `rootline-data`, Role `get,list,watch` on secrets with names `pg-rootline-migrator`, `pg-rootline-api`, `pg-rootline-agent`, `pg-rootline-faultlab`, `pg-rootline-console`, `pg-keycloak`; `ClusterSecretStore pg-roles` with `remoteNamespace: rootline-data` (PG-10) |
| `generators.yaml` | `Password` generators (`generators.external-secrets.io/v1alpha1`): `password-48` (`length: 48, digits: 8, symbols: 0, noUpper: false, allowRepeat: true`) for passwords and webhook tokens; `password-43` (`length: 43, digits: 8, symbols: 0, noUpper: false, allowRepeat: true`) for `job-token-key` and `bff-session-key`. Both are rendered into every namespace of `values.yaml` key `generatorNamespaces: [rootline-data, rootline, keycloak, observability]`, because a `generatorRef` resolves in the ExternalSecret's namespace (ADR 0046 T4; a namespaced generator, not a `ClusterGenerator`). Consumers derive the 32-byte AES key as `sha256(value)`; W4-T06 records this in `wiki/components/api.md` |

For every DB role, an `ExternalSecret pg-<role>` in `rootline-data` with `dataFrom: [{sourceRef: {generatorRef: {apiVersion: generators.external-secrets.io/v1alpha1, kind: Password, name: password-48}}}]`, `refreshInterval: "0"`, and `target.template` producing `type: kubernetes.io/basic-auth` with `username: <role>` and `password: "{{ .password }}"`.

- [ ] **Step 6: Write the empty umbrella chart and helpers**

`deploy/charts/rootline/templates/_helpers.tpl` defines, for later tasks: `rootline.podSecurityContext` (`runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001, fsGroup: 10001, seccompProfile: {type: RuntimeDefault}`), `rootline.containerSecurityContext` (`readOnlyRootFilesystem: true, allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}`), `rootline.image` (`{{ tpl .Values.image.registry (dict "Values" .Values) }}/{{ .component }}:{{ .Values.image.tag }}`; `tpl` evaluates the `{{ .Values.global.gcpProject }}` reference in `values-gke.yaml`, ADR 0046 T10), `rootline.probes` (`/healthz` liveness period 10 s, `/readyz` readiness period 5 s, both on port `http`), `rootline.otelEnv` (`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317`, `OTEL_SERVICE_NAME=rootline-<component>`), `rootline.keycloakTokenVolume` (projected SA token per SEC-033). `values.yaml`: `image: {registry: rootline, tag: dev, pullPolicy: IfNotPresent}`, `resources:` map per component from ARC-030 (memory only; no CPU values in W1, ADR 0046 T7), `security: {delegationMode: act}`, `llm: {clusterBudgetUsd: 6}`. `values-gke.yaml`: `image.registry: us-central1-docker.pkg.dev/{{ .Values.global.gcpProject }}/rootline`, `image.pullPolicy: IfNotPresent`. No templates yet render objects.

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

- [ ] **Step 8: Implement `scripts/render_manifests.py`** — for each env in `local`, `gke`, `ci`: `helm template` the root chart; for every Application of kind `local-chart`, run `helm template` on that chart path with `values.yaml` and `values-<env>.yaml` (if present) and `--set global.env=<env> --set global.domain=example.sslip.io`; print all documents to stdout separated by `---`. Exit 1 on any helm failure and on a `local-chart` path without `Chart.yaml` (stderr `render_manifests: chart not found: <path>`). Until W1-P3 integration step 3 the script also accepts `--allow-missing`, which turns a missing chart directory into the stderr line `skip <env> <name>: <path> not present`; step 3 removes the flag (ADR 0046 T8).

- [ ] **Step 9: Run tests and lint**

Run: `uv run pytest tests/repo/test_root_chart.py -v` → PASS.
Run: `uv run python scripts/render_manifests.py | kubeconform -strict -summary -ignore-missing-schemas -schema-location default -schema-location "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"` → 0 invalid.

- [ ] **Step 10: Wiki and commit** — create/update `wiki/components/argocd.md`, `cert-manager.md`, `external-secrets.md`, `traefik.md`, `kyverno.md` (installed; no policies yet), `chaos-mesh.md` with WIK-010 sections; log entry. Commit `feat(deploy): add k3d config and ArgoCD app-of-apps`.

---

### Task W1-T11: Observability stack and Postgres

**Requirement IDs:** WKL-020, WKL-021, WKL-022, WKL-023, ARC-002, ARC-010, ARC-030, DB-001, DB-002 (roles), GEN-050, PG-10, PG-27.
**Depends on:** W1-T10. **Branch:** `feat/w1-observability-postgres`.

> **Amended 2026-11-27 after the W1-T11 review of `feat/w1-observability-postgres` at `c35124d`, per PG-27 (overview §5; ADR 0046 `wiki/adr/0046-w1-t10-t11-review-decisions.md`).** Changed, with the ADR 0046 item in brackets: "Files" (`scripts/render_versions.py` gains `prometheus-operator-crds` in `CHART_KEYS`, T1, and the output `deploy/charts/platform-config/files/versions.yaml`, T11); Step 1 (the added required tests); Step 2 values block (`kubeControllerManager`, `kubeEtcd`, `kubeScheduler`, `kubeProxy` disabled, O5; the collector block: `logsCollection` preset off, explicit `file_log` receiver, `/var/log/pods` read-only `hostPath` only, UID 0 `securityContext`, new component names, O2, O3 item 2) and the paragraphs after it (DaemonSet `otel-collector-agent`, Service `otel-collector`, O1; network policies, O4); Step 3 (`rootline-data` policies, O4); Step 5 (`wiki/components/otel-collector.md` names DaemonSet `otel-collector-agent`, Service `otel-collector` and the O2 component names). W1-T11 is merged into `integration/w1-p3` before W1-T10 ("W1-P3 integration steps" under "Execution schedule" above).

**Files:**
- Create: `deploy/charts/observability/Chart.yaml` (dependencies: `kube-prometheus-stack`, `loki`, `tempo`, `opentelemetry-collector`, versions from `versions.yaml` — `scripts/render_versions.py` gains a step that rewrites the `dependencies` versions in this `Chart.yaml` and `--check` covers it), `values.yaml`, `values-local.yaml`, `values-gke.yaml`, `values-ci.yaml`, `templates/networkpolicies.yaml`
- Modify: `scripts/render_versions.py` — `CHART_KEYS` gains `"prometheus-operator-crds"` directly after `"kube-prometheus-stack"`; new constant `PLATFORM_CONFIG_KEYS = ["kubectl-image"]` and new output `deploy/charts/platform-config/files/versions.yaml` = `"# GENERATED by scripts/render_versions.py from versions.yaml. Do not edit.\n" + yaml.safe_dump({k: data[k] for k in PLATFORM_CONFIG_KEYS}, sort_keys=True)`, included in `render()` only when `deploy/charts/platform-config/Chart.yaml` exists; the module docstring lists both outputs (ADR 0046 T1, T11). Then run `uv run python scripts/render_versions.py` and commit the regenerated `deploy/root/files/versions.yaml` (always-allowed, overview §7.4)
- Create: `deploy/charts/postgres/{Chart.yaml,values.yaml,values-gke.yaml,templates/cluster.yaml,templates/database-keycloak.yaml,templates/networkpolicies.yaml}`
- Test: `tests/repo/test_observability_values.py`

- [ ] **Step 1: Write the failing test**

```python
"""Verifies WKL-020, WKL-021, WKL-023, DB-001, DB-002."""
from pathlib import Path

import yaml

from scripts.proc import run

REPO = Path(__file__).resolve().parents[2]


def tmpl(chart: str, env: str) -> list[dict]:
    args = ["helm", "template", "x", str(REPO / f"deploy/charts/{chart}"), "-f",
            str(REPO / f"deploy/charts/{chart}/values.yaml"), "--set", f"global.env={env}"]
    f = REPO / f"deploy/charts/{chart}/values-{env}.yaml"
    if f.exists():
        args += ["-f", str(f)]
    run(["helm", "dependency", "build", str(REPO / f"deploy/charts/{chart}")])
    return [d for d in yaml.safe_load_all(run(args).stdout) if d]


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

Required test expectations added by PG-27 (ADR 0046) in `tests/repo/test_observability_values.py`; each test's docstring cites the ADR item and the requirement ID in brackets:

| Test | Expectation |
|---|---|
| `test_collector_names` | env `local`: exactly one DaemonSet, named `otel-collector-agent`; Service `otel-collector` with ports 4317 and 4318; no Deployment from the collector chart (O1, WKL-020) |
| `test_collector_pipelines` | the rendered ConfigMap `otel-collector-agent` key `relay` has receivers exactly `{file_log, otlp}`, processors exactly `{batch, k8s_attributes, memory_limiter}`, exporters exactly `{otlp_grpc/tempo, otlp_http/loki, otlp_http/prometheus}`; pipelines `traces` = `otlp` → `memory_limiter, k8s_attributes, batch` → `otlp_grpc/tempo`, `metrics` = `otlp` → same processors → `otlp_http/prometheus`, `logs` = `otlp, file_log` → same processors → `otlp_http/loki`; `file_log.include` == `["/var/log/pods/shop_*/*/*.log", "/var/log/pods/rootline_*/*/*.log"]` (O2, WKL-020) |
| `test_collector_host_paths` | the DaemonSet pod spec has exactly one `hostPath` volume, `{path: /var/log/pods, type: Directory}`, mounted only at `/var/log/pods` with `readOnly: true`; no volume refers to `/var/lib/docker/containers`; container `securityContext` == `{runAsUser: 0, runAsGroup: 0, runAsNonRoot: False, allowPrivilegeEscalation: False, readOnlyRootFilesystem: True, capabilities: {drop: [ALL]}, seccompProfile: {type: RuntimeDefault}}` (O3, SEC-090) |
| `test_no_unreachable_control_plane_targets` | no rendered Service or ServiceMonitor name contains `kube-controller-manager`, `kube-etcd`, `kube-scheduler` or `kube-proxy`; ServiceMonitors whose names end in `-kubelet`, `-apiserver` and `-coredns` exist (O5) |
| `test_observability_network_policies` | the eight `observability` policies of ADR 0046 O4 with exactly the pod selectors, peers and ports of its table; `allow-otlp-ingress` selects `app.kubernetes.io/name: opentelemetry-collector`, `component: agent-collector`; `allow-operator-webhook-ingress` selects `app.kubernetes.io/name: kube-prometheus-stack-prometheus-operator`; `allow-egress-kubelet` selects `app.kubernetes.io/name: prometheus` and is the only policy that allows egress port 10250 (O4, ARC-010) |
| `test_postgres_network_policies` | the four `rootline-data` policies of ADR 0046 O4 (O4, DB-001) |
| `test_render_versions_chart_keys` | `deploy/root/files/versions.yaml` key `prometheus-operator-crds` equals the `versions.yaml` row; `scripts.render_versions.render()` has a key `deploy/charts/platform-config/files/versions.yaml` exactly when `deploy/charts/platform-config/Chart.yaml` exists, and its text parses to `{"kubectl-image": <versions.yaml row>}` (T1, T11, GEN-050) |

- [ ] **Step 2: Observability values** (`deploy/charts/observability/values.yaml`, keys nested under each dependency name)

```yaml
kube-prometheus-stack:
  grafana: {enabled: false}
  nodeExporter: {enabled: false}
  crds: {enabled: false}            # installed by the prometheus-crds Application (wave -3)
  defaultRules: {create: false}
  kubeControllerManager: {enabled: false}   # ADR 0046 O5: unreachable on k3s and GKE
  kubeEtcd: {enabled: false}
  kubeScheduler: {enabled: false}
  kubeProxy: {enabled: false}
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
  fullnameOverride: otel-collector        # Service otel-collector; DaemonSet otel-collector-agent (ADR 0046 O1)
  mode: daemonset
  service: {enabled: true}                # the chart creates no Service in daemonset mode by default
  image: {repository: otel/opentelemetry-collector-contrib}
  command: {name: otelcol-contrib}
  presets:
    kubernetesAttributes: {enabled: true}
    logsCollection: {enabled: false}      # ADR 0046 O3: the preset also mounts /var/lib/docker/containers
  securityContext:                        # ADR 0046 O3: UID 0 reads the root:root 0640 pod log files
    runAsUser: 0
    runAsGroup: 0
    runAsNonRoot: false
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities: {drop: [ALL]}
    seccompProfile: {type: RuntimeDefault}
  extraVolumes:
    - name: varlogpods
      hostPath: {path: /var/log/pods, type: Directory}
  extraVolumeMounts:
    - name: varlogpods
      mountPath: /var/log/pods
      readOnly: true
  resources: {requests: {memory: 192Mi}, limits: {memory: 384Mi}}
  ports:                                  # PSS baseline checks (warn/audit) and Kyverno forbid hostPort
    otlp: {enabled: true, hostPort: 0}
    otlp-http: {enabled: true, hostPort: 0}
    jaeger-compact: {enabled: false}
    jaeger-thrift: {enabled: false}
    jaeger-grpc: {enabled: false}
    zipkin: {enabled: false}
  config:                                 # component names of chart 0.183.2 (ADR 0046 O2)
    receivers:
      jaeger: null                        # null removes the chart-default components WKL-020 does not use
      zipkin: null
      prometheus: null
      otlp: {protocols: {grpc: {endpoint: "0.0.0.0:4317"}, http: {endpoint: "0.0.0.0:4318"}}}
      file_log:
        include: [/var/log/pods/shop_*/*/*.log, /var/log/pods/rootline_*/*/*.log]
        start_at: end
        include_file_path: true
        include_file_name: false
        retry_on_failure: {enabled: true}
        operators:
          - {type: container, id: container-parser, max_log_size: 102400}
    processors:
      memory_limiter: {check_interval: 1s, limit_percentage: 80, spike_limit_percentage: 20}
      batch: {}
    exporters:
      debug: null
      otlp_grpc/tempo: {endpoint: "tempo.observability.svc:4317", tls: {insecure: true}}
      otlp_http/prometheus: {endpoint: "http://prometheus-operated.observability.svc:9090/api/v1/otlp",
                             tls: {insecure: true}}
      otlp_http/loki: {endpoint: "http://loki.observability.svc:3100/otlp", tls: {insecure: true}}
    service:
      pipelines:
        traces: {receivers: [otlp], processors: [memory_limiter, k8s_attributes, batch], exporters: [otlp_grpc/tempo]}
        metrics: {receivers: [otlp], processors: [memory_limiter, k8s_attributes, batch],
                  exporters: [otlp_http/prometheus]}
        logs: {receivers: [otlp, file_log], processors: [memory_limiter, k8s_attributes, batch],
               exporters: [otlp_http/loki]}
```

The other keys of the `loki` and `tempo` blocks implemented on `feat/w1-observability-postgres` at `c35124d` stay (`enabled: true`, `fullnameOverride: loki`/`tempo`, `loki.sidecar.rules.enabled: false`, `tempo.tempo.reportingEnabled: false`); ADR 0046 does not change them.

The collector Service is named `otel-collector` and the collector runs as DaemonSet `otel-collector-agent` (chart naming for `fullnameOverride: otel-collector` and `mode: daemonset`; ADR 0046 O1). The chart keeps its default `rewriteDeprecatedComponentNames: true`, and the block above already uses the names the chart writes: receivers `otlp`, `file_log`; processors `memory_limiter`, `k8s_attributes` (added by the `kubernetesAttributes` preset), `batch`; exporters `otlp_grpc/tempo`, `otlp_http/prometheus`, `otlp_http/loki` (ADR 0046 O2). The only `hostPath` is `/var/log/pods`, read-only, `type: Directory`; PSS `baseline` forbids every `hostPath`, so namespace `observability` is PSS `privileged` with `warn` and `audit` at `baseline` (W1-T10 Step 4), and the W3-T12 Kyverno policy `disallow-privileged` restores the `baseline` checks for every other pod there (ADR 0046 O3, owner confirmation in "W1-P3 integration steps" step 5). Exact key names for `enableOTLPReceiver`/`otlp` depend on the resolved kube-prometheus-stack version: check `helm show values prometheus-community/kube-prometheus-stack --version <v> | grep -n -i otlp` and adapt; the test accepts either the field or the feature flag.

`values-gke.yaml`: `kube-prometheus-stack.prometheus.prometheusSpec.retention: 1d`, `loki.loki.limits_config.retention_period: 24h`, `tempo.tempo.retention: 24h`, collector `mode: daemonset` unchanged.
`values-ci.yaml`: `loki`, `tempo`, `opentelemetry-collector` disabled with `loki.enabled: false`, `tempo.enabled: false` and `opentelemetry-collector.enabled: false` (add `condition: <name>.enabled` to each of the three dependencies in `Chart.yaml`), Prometheus retention `6h`.

`templates/networkpolicies.yaml` (ADR 0046 O4; all ports TCP; namespaces matched by label `kubernetes.io/metadata.name`):

| Policy | Pod selector | Direction | Peer | Ports |
|---|---|---|---|---|
| `allow-same-namespace` | all pods (`{}`) | ingress | `podSelector: {}` (same namespace) | all |
| `allow-otlp-ingress` | `app.kubernetes.io/name: opentelemetry-collector`, `component: agent-collector` | ingress | `namespaceSelector: {}` | 4317, 4318 |
| `allow-query-ingress` | all pods | ingress | namespaces `rootline`, `observability` | 9090, 3100, 3200 |
| `allow-alertmanager-ingress` | all pods | ingress | namespace `observability` | 9093 |
| `allow-operator-webhook-ingress` | `app.kubernetes.io/name: kube-prometheus-stack-prometheus-operator` | ingress | `ipBlock: {cidr: 0.0.0.0/0}` (the kube-apiserver calls from a node or control-plane address) | 10250 |
| `allow-egress-pods` | all pods | egress | `namespaceSelector: {}` | all |
| `allow-egress-apiserver` | all pods | egress | `ipBlock: {cidr: 0.0.0.0/0}` | 443, 6443 |
| `allow-egress-kubelet` | `app.kubernetes.io/name: prometheus` | egress | `ipBlock: {cidr: 0.0.0.0/0}` (kubelet and cAdvisor on the node address) | 10250 |

DNS egress is the `allow-dns` policy of W1-T10 Step 4.

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

`database-keycloak.yaml`: CNPG `Database` resource `keycloak` (owner `keycloak`, cluster `rootline-pg`). `networkpolicies.yaml` (ADR 0046 O4; all ports TCP; every policy selects all pods): `allow-postgres-clients` (ingress 5432 from namespaces `rootline` and `keycloak`); `allow-cnpg-operator` (ingress 8000 and 5432 from namespace `cnpg-system`); `allow-same-namespace` (ingress from and egress to `podSelector: {}`); `allow-egress-apiserver` (egress to `ipBlock: {cidr: 0.0.0.0/0}` on 443 and 6443, for the CNPG instance manager and the initdb Job; 6443 is the k3s API server endpoint port, 443 the GKE one). No CPU request in W1; W3-T12 adds `resources.requests.cpu: 100m` to `cluster.yaml` (ADR 0046 T7). Pin `imageName` with the digest resolved in W1-T02 (`versions.yaml` key `postgres-image`).

- [ ] **Step 4: Run tests** → `uv run pytest tests/repo/test_observability_values.py -v` → PASS.

- [ ] **Step 5: Wiki and commit** — pages `kube-prometheus-stack.md`, `loki.md`, `tempo.md`, `otel-collector.md`, `postgres.md`; commit `feat(deploy): add observability stack and CNPG Postgres`.

---

### Task W1-T12: `task up` bring-up and memory budget

**Requirement IDs:** GEN-060 (`up`, `secrets:local`, `trust-ca`, `images`), S2, ARC-030, ARC-031, DB-001 (pgvector check), O-2, O-4, INF-020 (namespace rule), INF-021 (retry, Application `root`), INF-030 (node DNS), PG-28.
**Depends on:** W1-T10, W1-T11, O-2, O-4. **Branch:** `feat/w1-task-up`.

> **Amended 2026-11-27, per PG-27 (overview §5; ADR 0046 decisions T6, O3 item 3 and O4).** "Files" gains `.gitignore`; Step 3 item 1 names the `.gitignore` line; Step 5 gains the collector log-permission check and the Prometheus pod-label check.

> **Amended 2026-11-27 after the first `task up` on `feat/w1-task-up` (PR #30, report commit `7281427`), per PG-28 (overview §5; ADR 0047 `wiki/adr/0047-w1-t12-bringup-decisions.md`).** Changed, with the ADR 0047 item in brackets: Requirement IDs; "Files" (root chart files, `tests/repo/test_root_chart.py`, `wiki/components/argocd.md`; D1, D2); "Interfaces" (`SYNC_RETRY`, `ROOT_IGNORE_DIFFERENCES`, `NODE`, `strip_search_lines`, `fix_node_dns`, `root_application`; D2, D3, E1); Step 1 (the required test table); new Step 2b (root chart fixes; D1, D2); Step 3 (new item 2, node DNS, E1; item 6, the fields of Application `root`, D2, D3; items renumbered 1 to 9); Step 5 (checks for D1, D2, D3 and E1); Step 7 (troubleshooting rows). The fix round on `feat/w1-task-up` applies all of them, then reruns Steps 4, 5 and 8; the scratch branch `fix/w1-t12-verify-scratch` is not merged and is deleted after the rerun. Defect D4 (`workload` path missing) is not changed: it closes when W1-T09 steps 6 and 7 run in W1-S3.

> **Amended 2026-11-28 after the W1-T12 bring-up found Deployment `kafka` never Ready, per PG-29 (overview §5; ADR 0048 `wiki/adr/0048-kafka-kraft-voter-localhost.md`).** A fix round on `feat/w1-task-up` applies the W1-T09 changes of its amendment note of 2026-11-28 (ADR 0048 D1 to D3): `scripts/workload_transforms.py`, `scripts/render_workload.py`, `tests/repo/fixtures/otel-demo-mini.yaml`, `tests/repo/test_workload_render.py`, `wiki/components/workload.md` (W1-S3 is sequential, so no `owns` list applies, overview §7.4). Checks: `uv run pytest tests/repo/test_workload_render.py -v` → 26 passed; `uv run ruff format --check scripts tests/repo` and `uv run ruff check scripts tests/repo` → exit 0. Commit message: `fix(scripts): run the kafka KRaft voter on localhost in the workload render (PG-29)`. After review the coordinator re-renders into `rootline-env` as `baseline-v2` (ADR 0048 D3) and runs the live check (ADR 0048 D4), then Steps 5 and 8 are rerun. ADR 0047 D4 (`workload` path) is not affected (ADR 0048 D5). Step 6: a re-render for memory requests uses the next free tag, `baseline-v3`.

**Files:**
- Create: `scripts/up.py`, `scripts/secrets_local.py`, `scripts/trust_ca.py`, `scripts/build_images.py`, `scripts/wait_apps.py`
- Modify: `wiki/runbooks/local-up.md`, `wiki/components/capacity.md`, `wiki/components/otel-collector.md` and `wiki/components/kube-prometheus-stack.md` (Step 5 results); `deploy/charts/observability/values.yaml` only in the Step 5 `DAC_READ_SEARCH` fallback
- Modify: `.gitignore` — append, at the end of the file, exactly the two lines `# Generated k3d config (W1-T12, ADR 0046 T6)` and `infra/k3d/rootline.generated.yaml` (W1-S3 is sequential, so no `owns` list applies, overview §7.4)
- Modify (PG-28, Step 2b): `deploy/root/values.yaml` (a `namespace` key on every `apps` entry), `deploy/root/templates/apps.yaml` (destination line, `syncPolicy.retry`), `tests/repo/test_root_chart.py`; `wiki/components/argocd.md` (section "Defects found by W1-T12": column "Result" of D1, D2, D3 and the E1 paragraph state the PG-28 fix and the Step 5 result; sections "Interfaces" and "Configuration" list the `namespace` rule, the retry policy and the three fields of Application `root`)
- Test: `tests/repo/test_up_helpers.py`, `tests/repo/test_root_chart.py`

**Interfaces:**
- Produces: `scripts.wait_apps.wait_all(context: str, timeout_s: int) -> list[str]` (returns names not Synced/Healthy); `scripts.secrets_local.build_bootstrap_secret(env: dict[str,str]) -> dict` (Secret manifest with every non-empty `.env.local` key except `DEPLOY_KEY_*`, `ROOTLINE_ENV_DIR`, `ROOTLINE_HOST_ANTHROPIC_API_KEY`, `HF_USER`); `scripts.secrets_local.repo_secret(name: str, url: str, key_pem: str) -> dict`; `scripts.build_images.SERVICES` (list of image names that have a `Dockerfile`).
- Produces (PG-28, ADR 0047), all in `scripts/up.py`:

| Name | Type or signature | Value or behaviour | Errors |
|---|---|---|---|
| `SYNC_RETRY` | `dict[str, Any]` constant | `{"limit": 10, "backoff": {"duration": "10s", "factor": 2, "maxDuration": "3m"}}`; equal to the `retry` block of `deploy/root/templates/apps.yaml` (D2) | none |
| `ROOT_IGNORE_DIFFERENCES` | `list[dict[str, Any]]` constant | `[{"group": "argoproj.io", "kind": "Application", "jsonPointers": ["/metadata/finalizers"]}]` (D3) | none |
| `NODE` | `str` constant | `"k3d-rootline-server-0"`, the only kubelet node of INF-030 (`servers: 1`, `agents: 0`) | none |
| `root_application` | `(*, repo_url: str, revision: str, domain: str) -> dict[str, Any]` | the existing manifest plus `spec.ignoreDifferences = ROOT_IGNORE_DIFFERENCES` and `spec.syncPolicy = {"automated": {"prune": True, "selfHeal": True}, "syncOptions": ["RespectIgnoreDifferences=true"], "retry": SYNC_RETRY}` (D2, D3) | none (pure) |
| `strip_search_lines` | `(text: str) -> str` | pure; splits with `str.splitlines(keepends=True)`, drops every line whose first whitespace-separated token is `search` or `domain`, joins the rest unchanged (comments, blank lines, other lines and their line endings kept, order kept) (E1) | none |
| `fix_node_dns` | `(node: str = NODE, context: str = CONTEXT) -> bool` | Step 3 item 2 below; returns `True` when the file changed (E1) | `StepError("<command> exited <code>: <stderr>")` when a `docker exec` or `kubectl rollout restart` command exits non-zero; `StepError("<command> timed out after 60 s")` on `subprocess.TimeoutExpired`; `StepError("node DNS: search or domain line still present in <node>:/etc/resolv.conf")` when the re-read check fails. `kubectl get namespace argocd` exiting non-zero means "namespace absent" and is not an error |

`scripts/e2e.py up` (W6-T09 Step 3) imports `fix_node_dns`, `ROOT_IGNORE_DIFFERENCES` and `SYNC_RETRY`.

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

Required tests added by PG-28 (ADR 0047); each test's docstring cites the ADR item and the requirement ID in brackets. The fakes for `fix_node_dns` replace `scripts.up.run` with `monkeypatch.setattr(up, "run", fake)`, where `fake(cmd, *, check=True, capture=True, env=None, timeout=600, input_text=None)` records `(cmd, input_text)` and returns `subprocess.CompletedProcess(cmd, returncode, stdout, "")` from a per-test script of answers:

| Test | Expectation |
|---|---|
| `tests/repo/test_root_chart.py::test_waves_and_sync_policy` | additionally, for every rendered Application in `local`, `gke` and `ci`, `a["spec"]["syncPolicy"]["retry"] == scripts.up.SYNC_RETRY` (D2, INF-021) |
| `tests/repo/test_root_chart.py::test_application_namespaces` (new) | for `local`, `gke` and `ci`, every rendered Application's `spec.destination.namespace` equals `EXPECTED_NAMESPACES[name]`, a dict literal with the 17 entries of ADR 0047 D1 (`namespaces: argocd`, `gateway-api-crds: argocd`, `cert-manager: cert-manager`, `external-secrets: external-secrets`, `cnpg-operator: cnpg-system`, `kyverno: kyverno`, `chaos-mesh: chaos-mesh`, `prometheus-crds: observability`, `traefik: traefik`, `platform-config: argocd`, `postgres: rootline-data`, `observability: observability`, `keycloak: keycloak`, `argocd-accounts: argocd`, `rootline: rootline`, `workload: shop`, `demo-seed: rootline`); every key of `apps` in `deploy/root/values.yaml` is a key of the dict (D1, INF-020) |
| `tests/repo/test_root_chart.py::test_apps_contract_matches_plan` | additionally, every entry of `apps` in `deploy/root/values.yaml` has key `namespace` whose value is a non-empty `str` (D1) |
| `tests/repo/test_root_chart.py::test_missing_namespace_fails` (new) | `run(["helm", "template", "root", str(REPO / "deploy/root"), "--set", "env=local", "--set", "apps.observability.namespace=null"], check=False)` has `returncode != 0` and `"deploy/root/values.yaml apps.observability has no namespace"` in `stderr` (D1) |
| `tests/repo/test_up_helpers.py::test_root_application_manifest` | additionally `spec["ignoreDifferences"] == [{"group": "argoproj.io", "kind": "Application", "jsonPointers": ["/metadata/finalizers"]}]` and `spec["syncPolicy"] == {"automated": {"prune": True, "selfHeal": True}, "syncOptions": ["RespectIgnoreDifferences=true"], "retry": {"limit": 10, "backoff": {"duration": "10s", "factor": 2, "maxDuration": "3m"}}}` (D2, D3, INF-021) |
| `tests/repo/test_up_helpers.py::test_strip_search_lines` (new) | `strip_search_lines("nameserver 172.23.0.1\nsearch codegen.net\noptions ndots:0\n") == "nameserver 172.23.0.1\noptions ndots:0\n"`; `strip_search_lines("domain corp.example\nnameserver 10.0.0.1\n") == "nameserver 10.0.0.1\n"`; `strip_search_lines("search a b\n") == ""`; the inputs `"# search x\n\nnameserver 1.1.1.1"`, `"searchx a\n"` and `""` are returned unchanged (E1, INF-030) |
| `tests/repo/test_up_helpers.py::test_fix_node_dns_no_search_line` (new) | read answers `nameserver 172.23.0.1\n`; exactly one call, `["docker", "exec", "k3d-rootline-server-0", "cat", "/etc/resolv.conf"]`; returns `False` (E1) |
| `tests/repo/test_up_helpers.py::test_fix_node_dns_new_cluster` (new) | read answers `nameserver 172.23.0.1\nsearch codegen.net\n`, the re-read answers `nameserver 172.23.0.1\n`, `kubectl get namespace` exits 1; calls in this order: the read; `["docker", "exec", "-i", "k3d-rootline-server-0", "sh", "-c", "cat > /etc/resolv.conf"]` with `input_text == "nameserver 172.23.0.1\n"`; the read again; `["kubectl", "--context", "k3d-rootline", "get", "namespace", "argocd", "-o", "name"]`; no `rollout` call; returns `True` (E1) |
| `tests/repo/test_up_helpers.py::test_fix_node_dns_existing_argocd` (new) | as the previous test, but `kubectl get namespace` exits 0; the calls end with `["kubectl", "--context", "k3d-rootline", "-n", "argocd", "rollout", "restart", "deployment"]` and then `[..., "rollout", "restart", "statefulset"]`; returns `True` (E1) |
| `tests/repo/test_up_helpers.py::test_fix_node_dns_write_not_applied` (new) | the re-read still answers `search codegen.net\n`; raises `StepError` whose message is `node DNS: search or domain line still present in k3d-rootline-server-0:/etc/resolv.conf` (E1) |

- [ ] **Step 2: Implement `secrets_local.py`** — builds both manifests and applies them with `kubectl --context k3d-rootline apply -f -` (via `scripts.proc.run(..., input_text=yaml.safe_dump(...))`). Namespaces `rootline-secrets` and `argocd` are created with `kubectl create namespace --dry-run=client -o yaml | kubectl apply -f -` equivalents in Python (build the Namespace manifest and apply) when missing.

- [ ] **Step 2b: Root chart fixes (PG-28, ADR 0047 D1 and D2)** — in `deploy/root/values.yaml`, give every `apps` entry the `namespace` key of the "Task W1-T10" root values block (new keys: `namespaces: argocd`, `gateway-api-crds: argocd`, `platform-config: argocd`, `postgres: rootline-data`, `observability: observability`, `keycloak: keycloak`, `argocd-accounts: argocd`, `rootline: rootline`, `workload: shop`, `demo-seed: rootline`; the other seven entries already have theirs), placed directly after `path` (or after `versionKey` for `gateway-api-crds`, after `path` and before `envs` for `demo-seed`); and add a comment line above `apps:`, exactly `# Every entry MUST have \`namespace\` (spec INF-020, ADR 0047 D1); apps.yaml has no default.` In `deploy/root/templates/apps.yaml`, replace the destination `namespace:` line and append the `retry` block exactly as in "Task W1-T10" Step 3. Then run `uv run pytest tests/repo/test_root_chart.py -v` → PASS and `uv run python scripts/render_manifests.py > /dev/null` → exit 0.

- [ ] **Step 3: Implement `up.py`** — steps in order, each printing `==> <step>`:
  1. `k3d cluster list -o json`; if `rootline` absent, write `infra/k3d/rootline.generated.yaml` (substitute `<versions.k3s>` with the tag where `+` becomes `-`, and `<repo>` with the absolute repository path inside WSL, `/home/arkhash0309/projects/rootline`) and run `k3d cluster create --config infra/k3d/rootline.generated.yaml`. The generated file is ignored by the `.gitignore` line of "Files"; `infra/k3d/rootline.yaml` keeps both placeholders (INF-030, ADR 0046 T6).
  2. Node DNS (`==> node DNS search list`, PG-28, ADR 0047 E1), on every run, also when the cluster already existed: `fix_node_dns()` (see "Interfaces"). (a) Read `docker exec k3d-rootline-server-0 cat /etc/resolv.conf`. (b) `new = strip_search_lines(text)`; when `new == text`, print `node DNS: k3d-rootline-server-0 has no search or domain line` and continue with item 3. (c) Write `new` with `docker exec -i k3d-rootline-server-0 sh -c 'cat > /etc/resolv.conf'` (stdin = `new`; `cat >` writes through Docker's bind mount, a rename would fail). (d) Read the file again as in (a); when `strip_search_lines(reread) != reread`, raise `StepError("node DNS: search or domain line still present in k3d-rootline-server-0:/etc/resolv.conf")`. Print `node DNS: removed search and domain lines from k3d-rootline-server-0:/etc/resolv.conf`. (e) When `kubectl --context k3d-rootline get namespace argocd -o name` exits 0, run `kubectl --context k3d-rootline -n argocd rollout restart deployment` and `kubectl --context k3d-rootline -n argocd rollout restart statefulset`, and print `node DNS: restarted deployments and statefulsets in namespace argocd`. Every command has timeout 60 s. The `kube-system` pods that k3s starts during `k3d cluster create` keep the old list and are not restarted (CoreDNS `forward . /etc/resolv.conf` does not apply a search list; Traefik, metrics-server, local-path-provisioner and `svclb-traefik` resolve no external names). Docker does not rewrite an edited `resolv.conf`, so the change survives `task stop`/`task start`; `task down` removes it with the container.
  3. `scripts/build_images.py --tag dev --import-k3d rootline` (skips when no service has a Dockerfile yet).
  4. `helm repo add argo <repo>` and `helm upgrade --install argocd argo/argo-cd --version <chart> -n argocd --create-namespace -f deploy/upstream/argo-cd/values-local.yaml --wait --timeout 10m`.
  5. `scripts/secrets_local.py`.
  6. Render `deploy/root` with `--set env=local,domain=127.0.0.1.sslip.io,targetRevision=<--revision>` and apply `root_application()` as Application `root` with `kubectl apply`: project `default`, source `deploy/root`, those parameters, `spec.ignoreDifferences: [{group: argoproj.io, kind: Application, jsonPointers: [/metadata/finalizers]}]`, `spec.syncPolicy: {automated: {prune: true, selfHeal: true}, syncOptions: [RespectIgnoreDifferences=true], retry: {limit: 10, backoff: {duration: 10s, factor: 2, maxDuration: 3m}}}` (PG-28, ADR 0047 D2 and D3). The field is set here and not in `deploy/root`, because the root chart renders only the child Applications; ArgoCD `v3.6.3` adds PreDelete finalizers to a child whose chart has a PreDelete hook (`kyverno`), and without the entry `root` stays `OutOfSync`.
  7. `scripts/wait_apps.py --timeout 1200`; on timeout print the unhealthy apps with `kubectl -n argocd get applications` output and exit 1. The expected names are `root` and every rendered child, so this item depends on item 6's `ignoreDifferences` (ADR 0047 D3).
  8. Print the ArgoCD admin password from secret `argocd/argocd-initial-admin-secret` key `password` and the URLs `https://argocd.127.0.0.1.sslip.io`.
  9. Run `scripts/doctor.py` memory check and print `memory_requests_total`.

The module docstring of `scripts/up.py` lists these nine steps in this order.

`trust_ca.py`: reads secret `cert-manager/rootline-local-ca` key `ca.crt` (or with `--env gke` the GKE fallback CA secret named in INF-041), writes it to `data/rootline-ca.crt`, then (GEN-060, PG-17): (1) `sudo install -m 0644 data/rootline-ca.crt /usr/local/share/ca-certificates/rootline-ca.crt && sudo update-ca-certificates` (prompts for the sudo password in the terminal); (2) `certutil -d sql:$HOME/.pki/nssdb -A -t C,, -n rootline-local-ca -i data/rootline-ca.crt` after creating the database with `certutil -d sql:$HOME/.pki/nssdb -N --empty-password` if absent; (3) `/mnt/c/Windows/System32/certutil.exe -user -addstore Root <wslpath -w data/rootline-ca.crt>` through WSL interop (absolute path: `appendWindowsPath=false`) (Windows shows a confirmation dialog the owner accepts). Each step prints `OK`/`FAIL`; the script exits 1 if any failed. It refuses to run outside WSL (no `WSL_DISTRO_NAME`) unless `--linux-only` is passed (CI uses `--linux-only`, which skips step 3).

`build_images.py`: `--tag <t>`, `--import-k3d <cluster>` or `--load-kind <cluster>` or `--push <registry>`; image list = every `services/*/Dockerfile` (image name = directory name) plus `apps/console/Dockerfile` (`console`); build args `PYTHON_IMAGE`, `UV_IMAGE`, `NODE_IMAGE` from `versions.yaml` (`repo@digest`); build context = repo root; `docker buildx build --load -f <Dockerfile> -t rootline/<name>:<tag> --build-arg ... .`; then `k3d image import -c <cluster> rootline/<name>:<tag> ...`.

- [ ] **Step 4: Run tests** → `uv run pytest tests/repo/test_up_helpers.py -v` → PASS.

- [ ] **Step 5: Bring up the cluster**

Run: `task up`. Expected: all apps `Synced/Healthy` within 20 min (the `rootline` app is Healthy with zero resources; `workload` is Healthy).

Verify pgvector (DB-001):

```bash
kubectl -n rootline-data exec rootline-pg-1 -- psql -U postgres -d rootline -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Expected: a `0.8.x` version.

Verify the collector and network-policy assumptions of ADR 0046 (O3 item 3, O4), after the cluster has run for 5 min:

```bash
kubectl -n observability logs ds/otel-collector-agent | grep -ci "permission denied"
kubectl -n observability get pods -l app.kubernetes.io/name=prometheus -o name
kubectl -n observability get pods -l app.kubernetes.io/name=kube-prometheus-stack-prometheus-operator -o name
```

Expected: the first command prints `0`; the second and third each print exactly one pod. If the first prints more than `0`, add `DAC_READ_SEARCH` to `capabilities.add` of the collector container in `deploy/charts/observability/values.yaml`, re-sync, and repeat; if it still prints more than `0`, report `STATUS: BLOCKED`. If the second or third prints nothing, report `STATUS: BLOCKED` with `kubectl -n observability get pods --show-labels`, because the O4 policies select those labels. Record the three outputs in `wiki/components/otel-collector.md` and `wiki/components/kube-prometheus-stack.md`.

Verify the PG-28 fixes (ADR 0047), after `task up` exited 0:

```bash
kubectl --context k3d-rootline -n observability get pods -o name | grep -c .
kubectl --context k3d-rootline -n argocd get pods -l app.kubernetes.io/instance=observability -o name | grep -c .
kubectl --context k3d-rootline -n argocd get applications -o jsonpath='{range .items[*]}{.metadata.name} {.spec.destination.namespace} {.spec.syncPolicy.retry.limit}{"\n"}{end}'
kubectl --context k3d-rootline -n argocd get application root -o jsonpath='{.status.sync.status} {.status.health.status}{"\n"}'
kubectl --context k3d-rootline -n argocd get application kyverno -o jsonpath='{.metadata.finalizers}{"\n"}'
kubectl --context k3d-rootline -n rootline-data get externalsecret -o name
docker exec k3d-rootline-server-0 grep -cE '^(search|domain)[[:space:]]' /etc/resolv.conf
kubectl --context k3d-rootline -n argocd exec deploy/argocd-repo-server -c repo-server -- grep '^search' /etc/resolv.conf
kubectl --context k3d-rootline -n argocd exec deploy/argocd-repo-server -c repo-server -- getent hosts github.com
```

Expected, in order: (1) a number of at least `1` (D1); (2) `0` (grep exits 1; D1); (3) one line per Application, the namespace equal to ADR 0047 D1 (`root`: `argocd`), and `10` on every line, `root` included (D2); (4) `Synced Healthy` (D3); (5) a list that contains `resources-finalizer.argocd.argoproj.io` (D3); (6) six lines, `externalsecret.external-secrets.io/pg-keycloak`, `pg-rootline-agent`, `pg-rootline-api`, `pg-rootline-console`, `pg-rootline-faultlab`, `pg-rootline-migrator` (D2); (7) `0` (grep exits 1; E1); (8) exactly `search argocd.svc.cluster.local svc.cluster.local cluster.local` (E1); (9) one line with name `github.com` and an address other than `79.72.77.199` (E1). Then push one more commit to the tracked branch (the wiki commit of Step 9 is enough) and repeat (4) and (5) after `root` has synced the new revision (`kubectl -n argocd get application root -o jsonpath='{.status.sync.revision}'` equals the new commit): (4) still `Synced Healthy` and (5) still lists the two `pre-delete-finalizer.argocd.argoproj.io` entries, which shows that `RespectIgnoreDifferences=true` keeps them. If any expectation fails, report `STATUS: BLOCKED` with the command output; do not change the decision. Record the outputs in `wiki/components/argocd.md` section "Defects found by W1-T12".

If the pgvector check fails, build `deploy/images/postgres/Dockerfile` (`FROM ghcr.io/cloudnative-pg/postgresql:16` + `apt-get install -y postgresql-16-pgvector`), record the decision in an ADR (next free number), set `postgres-image` in `versions.yaml`, and re-run.

- [ ] **Step 6: Measure memory (S2)** — `task doctor` → `memory_requests_total` ≤ 9.5 GiB. Write `wiki/components/capacity.md`: a table of every pod's memory request from `kubectl get pods -A -o json` (component, namespace, request, limit) and the total, dated. If > 9.5 GiB, apply ARC-031 reductions in order, recording each with the new total. The workload budget (≤ 3.2 GiB, ARC-030) is checked by summing namespace `shop`; if it exceeds 3.2 GiB, set per-component requests in the render values (`components.<name>.resources.requests.memory`) to bring the sum under 3.2 GiB and re-render (this is a re-render that raises `BASELINE_TAG` in `scripts/render_workload.py` by 1, to `baseline-v3` after the PG-29 re-render, and follows the PR procedure of ADR 0048 D3 with that tag, WKL-001).

- [ ] **Step 7: Run `task trust-ca`** and open `https://argocd.127.0.0.1.sslip.io` in the Windows browser (`/mnt/c/Windows/explorer.exe "https://argocd.127.0.0.1.sslip.io"` from WSL); log in as `admin`. Record the result in `wiki/runbooks/local-up.md`, which now documents: prerequisites, `.env.local` keys for week 1, `task up`, expected duration, URLs, admin password retrieval, `task stop/start/down`, and troubleshooting (apps stuck `Progressing` → `kubectl -n argocd get applications`, `argocd app get` via UI). The "Troubleshooting" table of `wiki/runbooks/local-up.md` has, per PG-28 (ADR 0047), exactly these rows in addition to the ones above, and no longer gives the manual `resolv.conf` workaround as the fix:

| Symptom | Cause and command |
|---|---|
| Every Application `Unknown`; repo-server log `failed to list refs: dial tcp <ip>:22: connect: connection timed out` | A DNS search domain of the workstation (`search` line of WSL `/etc/resolv.conf`, copied from Windows) answers `github.com.<domain>` with a wildcard address. `task up` step "node DNS search list" removes the line from `k3d-rootline-server-0:/etc/resolv.conf` (ADR 0047 E1); rerun `task up`. Check with `kubectl -n argocd exec deploy/argocd-repo-server -c repo-server -- getent hosts github.com` (a GitHub address, not the wildcard address) |
| Applications `Unknown` with `TLS handshake timeout` or `context deadline exceeded` towards `github.com` | the workstation's connection to GitHub is slow or down (not E1); check with `curl -sS -o /dev/null --max-time 20 https://github.com`; ArgoCD retries the sync with `syncPolicy.retry` (ADR 0047 D2) |
| An Application shows `operationState.phase: Failed` after ten retries | the cause persisted for 1210 s; fix it, then start one sync: `kubectl --context k3d-rootline -n argocd patch application <name> --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{}}}'` |
| A sync stays `Running` on an old revision (for example `observability` waiting for a DaemonSet in the wrong namespace) | `kubectl --context k3d-rootline -n argocd patch application <name> --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'` |
| Application `root` `OutOfSync` with only `Application/<child>` listed | Application `root` lacks the `ignoreDifferences` of ADR 0047 D3; rerun `task up`, which applies `root_application()` again |

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

- [ ] **Step 5: Run the gate (WKL-004)** — `uv run python scripts/baseline_gate.py --minutes 30`. On FAIL, follow WKL-004 (re-enable the missing dependency in `deploy/upstream/otel-demo/values.yaml` or disable the load-generator task via its documented env var), re-render (raise `BASELINE_TAG` in `scripts/render_workload.py` by 1, the next free tag, `baseline-v3` unless W1-T12 Step 6 used it; PR procedure of ADR 0048 D3 with that tag; WKL-001, PG-29), re-run until PASS. Record the outcome table in `wiki/components/workload.md`.

- [ ] **Step 6: Alert rules template** — `prometheusrule-workload.yaml` renders `PrometheusRule rootline-workload` in `observability` from `metric-map.yaml` and `alert-thresholds.yaml` (copied into `deploy/charts/observability/files/` by `derive_thresholds.py`). One rule group `rootline-workload`; per-service rules are generated with one rule per (alert, service) for the per-service alerts and one rule for the cluster-wide kube-state-metrics alerts. Every rule has labels `rootline: "true"`, `namespace: shop`, `service: <svc>` (for kube-state-metrics rules: `service` is derived with `label_replace(..., "service", "$1", "pod", "(.*)-[a-z0-9]+-[a-z0-9]+")` for Deployment pods and `"$1", "pod", "(.*)-[0-9]+"` for StatefulSets), `severity`, and annotation `summary`. Expressions, `for` and severities exactly as the WKL-031 table. `HighCPU`/`HighMemory` use `kube_pod_container_resource_limits{resource="cpu|memory"}`; services without limits are excluded by the `and` on the limit series.

Test (`tests/repo/test_alert_rules.py`): render the chart, load the `PrometheusRule`, assert there is exactly one rule named `ServiceHighErrorRate` per kept server-side service with `for: 1m`, `labels.severity == "critical"`, `labels.rootline == "true"`, and that the expression text contains `> 0.05` and `> 0.1`; assert `PodCrashLooping` has `for: 0m`; run `promtool check rules` on the extracted rule file when `promtool` is on PATH (skip otherwise).

- [ ] **Step 7: Alertmanager config** — `alertmanager-config.yaml` renders an `AlertmanagerConfig` (or the chart's `alertmanager.config` values; choose `AlertmanagerConfig` CRD with `alertmanagerConfigMatcherStrategy: None` set in values) with route `group_by: [alertname, service]`, `group_wait: 30s`, `group_interval: 2m`, `repeat_interval: 1h`, single receiver `rootline-api` webhook `http://api.rootline.svc.cluster.local/hooks/alertmanager`, `sendResolved: true`, `httpConfig.authorization.credentials: {name: alertmanager-webhook, key: token}`. The Secret `observability/alertmanager-webhook` comes from an ExternalSecret using generator `password-48` (created now in `platform-config`; the `rootline` copy comes in W4-T13 via the same generated value — use a `PushSecret`-free approach: the ExternalSecret in `observability` generates it, and an ExternalSecret in `rootline` reads it through a ClusterSecretStore `observability-reader` (Kubernetes provider, remote namespace `observability`, Role limited to secret `alertmanager-webhook`)).

- [ ] **Step 8: Verify** — sync, then `kubectl -n observability get prometheusrules rootline-workload -o yaml | grep -c "alert:"` equals the expected rule count printed by the test; Prometheus UI `/alerts` shows the rules in state `inactive`.

- [ ] **Step 9: Commit** `feat(deploy): add workload alert rules, thresholds and baseline gate` with wiki updates.

---

### Task W1-T14: CI workflow `ci.yml` and repository ruleset

**Requirement IDs:** CI-001 (`ci.yml`), CI-002, GEN-020, GEN-021, GEN-050, WIK-020, O-3, PG-21, PG-26.
**Depends on:** W1-T01 … W1-T13 merged or on the same branch. **Branch:** `feat/w1-ci`.

> **Amended 2026-11-27 after the W1-T14 review of `feat/w1-ci` at `8b2ce1c`, per PG-26 (overview §5; ADR 0045 decisions D1 to D6).** Changed: "Requirement IDs"; "Files" (the two ruleset files and `tests/repo/test_ci_changed_files.py`, D1); the new "Interfaces" section (`scripts/ci_changed_files.py`, D2, and the required tests, D1); the Step 1 `ci.yml` block (`name: ci / required`, D3; `V_UV` in all five `setup-uv` steps, the `versions.env` step in `contracts`, `wiki` and `security`, `V_TRIVY`, `V_GITLEAKS`, D5; the `wiki` job calls `scripts/ci_changed_files.py`, D2); the paragraph after the block (SHAs only in `ci.yml`, D6; Python versions, D5); Step 2 and Step 3 (verification commands, D3; `main.json` without `required_linear_history` and the full `develop.json`, D4). `tests/repo/test_ci_changed_files.py` is in W1-T14's `owns` in `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`. The W1-T14 implementer rebases `feat/w1-ci` onto the `develop` commit that contains ADR 0045 (`git fetch origin && git rebase origin/develop`, then `git push --force-with-lease origin feat/w1-ci`) before it runs `uv run python scripts/check_ownership.py --task W1-T14 --base origin/develop --branch HEAD`, because that script reads the schedule YAML from the checkout it runs in.

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/rulesets/main.json`, `.github/rulesets/develop.json`, `scripts/ci_changed_files.py`
- Modify: `wiki/runbooks/github-apps.md` (section `## Rulesets`)
- Test: `tests/repo/test_ci_changed_files.py` (PG-26, ADR 0045 D1)

**Interfaces (PG-26, ADR 0045 D2):**
- Produces: CLI `uv run python scripts/ci_changed_files.py --base <ref> --head <ref> [--output <file>] [--repo <dir>]`, run from the repository root.

| Option | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `--base` | string (git revision) | yes | — | Base revision, for example `origin/develop` |
| `--head` | string (git revision) | yes | — | Head revision, for example `HEAD` |
| `--output` | file path | no | none: write to stdout | File to write (UTF-8, created or overwritten); a relative path resolves against the working directory |
| `--repo` | directory path | no | `REPO = Path(__file__).resolve().parents[1]` (the repository that contains the script) | Repository passed to `git -C` |

  Behaviour, in this order: (1) if `Path(repo).is_dir()` is `False`, fail with reason `repo not found: <dir>` without starting `git`; (2) run, through `scripts.proc.run(cmd, check=True, timeout=120)`, the argument list `["git", "-C", str(repo), "diff", "--name-only", "--diff-filter=ACMRD", "--no-renames", "-z", f"{base}...{head}"]` (no shell; three-dot form = changes on `<head>` since the merge base; a rename is listed as the deleted old path plus the added new path, PG-21); (3) split stdout on `"\0"`, drop empty strings, sort with `sorted()`, build `text = "".join(f"{p}\n" for p in paths)` (one path per line, LF, nothing else; empty change set = empty string); (4) with `--output`, write `text` in one `Path(output).write_text(text, encoding="utf-8")` call and print nothing to stdout; without `--output`, write `text` to stdout. It writes no other file, never changes the repository and makes no network call. It does not validate ref syntax; callers MUST pass refs that do not start with `-` (CI passes `origin/<base_ref>` and `HEAD`).

| Case | When it occurs | stderr (exact, one line) | Exit |
|---|---|---|---|
| Success | `git` exits 0 and the output is written | nothing | 0 |
| Repository missing | `--repo` is not an existing directory | `ci_changed_files: repo not found: <dir>` (`<dir>` = the `--repo` value as given, or `str(REPO)` for the default) | 2 |
| `git` missing | starting `git` raises `FileNotFoundError` | `ci_changed_files: git missing` | 2 |
| Timeout | `git` does not finish within 120 s (`subprocess.TimeoutExpired`) | `ci_changed_files: timeout` | 2 |
| `git` exits non-zero | unknown revision, no merge base, `--repo` is not a git repository (`subprocess.CalledProcessError`) | `ci_changed_files: git failed: <msg>`; `<msg>` = first line of `exc.stderr.strip()`, or `exit <returncode>` when that is empty. Example (git `2.53.0`): `ci_changed_files: git failed: fatal: ambiguous argument 'origin/nope...HEAD': unknown revision or path not in the working tree.` | 2 |
| `git` cannot start for another reason | starting `git` raises an `OSError` other than `FileNotFoundError` | `ci_changed_files: git failed: <str(exc)>` | 2 |
| `git` output not UTF-8 | `UnicodeDecodeError` while decoding stdout | `ci_changed_files: git failed: <str(exc)>` | 2 |
| Output not writable | `--output` given and `write_text` raises `OSError` | `ci_changed_files: output not writable: <path>` (`<path>` = the `--output` value as given); no retry, no cleanup of a partly written file | 2 |
| Usage error | `--base` or `--head` missing, unknown option | argparse's two lines `usage: …` and `ci_changed_files.py: error: <message>` | 2 |

  On every failure except "Output not writable", nothing is written to stdout and no `--output` file is created or changed. No other exception is caught: a traceback with exit 1 means a defect in the script.
- Produces (Python, used by the tests): `class ChangedFilesError(Exception)` (`str(exc)` = the reason without the `ci_changed_files: ` prefix); `changed_files(base: str, head: str, repo: Path = REPO, *, timeout: int = 120) -> list[str]` (behaviour steps 1 to 3; raises `ChangedFilesError` with reason `repo not found: <dir>`, `git missing`, `timeout` or `git failed: <msg>`); `main(argv: Sequence[str] | None = None) -> int` (parses, calls `changed_files`, performs step 4, prints the stderr line and returns the exit code of the table).
- Consumes: `scripts.proc.run` (W1-T06). The module starts with `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` before `from scripts.proc import run` (PG-21 item 9).

**Required tests** (`tests/repo/test_ci_changed_files.py`, PG-26, ADR 0045 D1). The module docstring cites CI-001, WIK-020 and PG-21; every test docstring cites at least one of them. Each test builds a throw-away repository under `tmp_path` with `git` through `scripts.proc.run` (`git init -b main`, `git -c user.name=t -c user.email=t@example.invalid commit`), as `tests/repo/test_check_ownership.py` does, and makes no network call.

| # | Test function | Set-up | Assertion |
|---|---|---|---|
| 1 | `test_lists_added_modified_deleted_sorted` | base commit with `b.txt`, `c.txt`; branch adds `z.txt`, `a.txt`, modifies `b.txt`, deletes `c.txt` | `changed_files("main", "HEAD", repo) == ["a.txt", "b.txt", "c.txt", "z.txt"]` |
| 2 | `test_rename_lists_old_and_new_path` | branch runs `git mv old.txt new.txt` | result `== ["new.txt", "old.txt"]` |
| 3 | `test_three_dot_ignores_later_base_commits` | after branching, `main` gains `late.txt`; branch adds `mine.txt` | result `== ["mine.txt"]` |
| 4 | `test_empty_change_set` | repository with one commit on `main`; `main(["--base", "main", "--head", "main", "--repo", str(repo), "--output", str(out)])` | return value `0` and `out.read_text(encoding="utf-8") == ""` |
| 5 | `test_output_file_format` | test 1's repository, `--output out.txt` | exit 0, file bytes `b"a.txt\nb.txt\nc.txt\nz.txt\n"`, `capsys` stdout `""` |
| 6 | `test_stdout_without_output` | test 1's repository, no `--output` | exit 0, stdout `"a.txt\nb.txt\nc.txt\nz.txt\n"` |
| 7 | `test_unknown_ref_exits_2` | `--base nope` | exit 2, stderr is one line starting `ci_changed_files: git failed: `, stdout `""` |
| 8 | `test_repo_not_found_exits_2` | `--repo <tmp_path>/missing` | exit 2, stderr `f"ci_changed_files: repo not found: {tmp_path / 'missing'}\n"` |
| 9 | `test_output_not_writable_exits_2` | `--output <tmp_path>/no-dir/out.txt` | exit 2, stderr `f"ci_changed_files: output not writable: {tmp_path / 'no-dir' / 'out.txt'}\n"` |
| 10 | `test_git_missing_exits_2` | `monkeypatch.setattr(ci_changed_files, "run", <fake raising FileNotFoundError("git")>)` | exit 2, stderr `"ci_changed_files: git missing\n"` |
| 11 | `test_timeout_exits_2` | fake `run` raising `subprocess.TimeoutExpired(cmd=["git"], timeout=120)` | exit 2, stderr `"ci_changed_files: timeout\n"` |

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
        with: {version: "v${{ env.V_TRIVY }}", scan-type: config, scan-ref: infra/terraform, exit-code: "1", severity: "CRITICAL,HIGH"}
  manifests:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: astral-sh/setup-uv@v6
        with: {version: "${{ env.V_UV }}"}
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
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: astral-sh/setup-uv@v6
        with: {version: "${{ env.V_UV }}"}
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
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: astral-sh/setup-uv@v6
        with: {version: "${{ env.V_UV }}"}
      - run: uv run python scripts/wiki_lint.py
      - if: github.event_name == 'pull_request'
        env: {GH_TOKEN: "${{ github.token }}"}
        run: |
          uv run python scripts/ci_changed_files.py --base "origin/${{ github.base_ref }}" --head HEAD --output changed.txt
          gh pr view ${{ github.event.pull_request.number }} --json body --jq .body > body.txt
          uv run python scripts/wiki_lint.py --changed-files changed.txt --pr-body body.txt
  security:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - run: cat .github/versions.env >> "$GITHUB_ENV"
      - uses: gitleaks/gitleaks-action@v2
        env: {GITHUB_TOKEN: "${{ github.token }}", GITLEAKS_VERSION: "${{ env.V_GITLEAKS }}"}
      - uses: astral-sh/setup-uv@v6
        with: {version: "${{ env.V_UV }}"}
      - run: uv export --all-packages --frozen --no-hashes > requirements.txt && uvx pip-audit -r requirements.txt
      - if: ${{ hashFiles('apps/console/package-lock.json') != '' }}
        run: npm --prefix apps/console audit --audit-level=high
  required:
    name: ci / required    # check-run name = ruleset context `ci / required` (GEN-020, PG-26 D3)
    if: always()
    needs: [python, console, policy, infra, manifests, contracts, wiki, security]
    runs-on: ubuntu-24.04
    steps:
      - run: |
          echo '${{ toJSON(needs) }}' > needs.json
          python3 -c "import json,sys;n=json.load(open('needs.json'));bad=[k for k,v in n.items() if v['result'] not in ('success','skipped')];print('failed:',bad);sys.exit(1 if bad else 0)"
```

`uv run ruff format --check .` stays exactly as written. Do not add a `uv run ruff format .` step and do not reformat any file in this task: Markdown files are excluded from ruff by `extend-exclude = ["*.md"]` in the root `pyproject.toml`, and `tests/repo/test_layout.py` is already ruff-formatted (both done by W1-T16 Step 0, PG-19). W1-T14 runs in the parallel stage W1-P3 and may change only its `owns` paths (overview §7.4); a repository-wide reformat would change files owned by W1-T09, W1-T10 and W1-T11 and fail gate check G1. If the `python` job's format step fails on a file, the failure belongs to the task that last changed that file (overview §7.8).

`V_*` variables come from `.github/versions.env` (W1-T02), loaded by `run: cat .github/versions.env >> "$GITHUB_ENV"` after `actions/checkout` in every job that uses one (PG-26, ADR 0045 D5): `setup-uv` gets `version: "${{ env.V_UV }}"` in all five jobs that use it (`python`, `manifests`, `contracts`, `wiki`, `security`); `trivy-action` gets `version: "v${{ env.V_TRIVY }}"` (with `v` prefix); `gitleaks-action` gets step env `GITLEAKS_VERSION: "${{ env.V_GITLEAKS }}"` (no `v` prefix). Only the `python` job runs `uv python install ${{ env.V_PYTHON }}`; `manifests`, `contracts`, `wiki` and `security` accept any CPython 3.12.x that satisfies `requires-python = ">=3.12,<3.13"` (explicit choice, cheapest: no extra step). `azure/setup-helm` keeps its default Helm version (`versions.yaml` has no Helm CLI key). The `required` job MUST keep `name: ci / required` (D3). Third-party action versions above are the major versions current on the planning date; on the pin date use the latest release of each and pin it by commit SHA (`uses: owner/action@<40-hex sha> # vX.Y.Z`). The SHA and tag are recorded only in that `uses:` line of `ci.yml`; W1-T14 does not edit `wiki/versions.md` (owned by W1-T02, PG-22). W1-T02 Step 8 (deferred to W1-S3) copies them into the `## GitHub Actions` table of `wiki/versions.md` (PG-26, ADR 0045 D6). `scripts/check_contracts.py` is created in W4-T06.

- [ ] **Step 1b: Write `scripts/ci_changed_files.py` and its tests** (PG-26, ADR 0045 D1, D2) — write the eleven "Required tests" in `tests/repo/test_ci_changed_files.py` first and run `uv run pytest tests/repo/test_ci_changed_files.py -v` → FAIL; implement the script per "Interfaces" above; run the same command → 11 passed; then `uv run ruff format scripts/ci_changed_files.py tests/repo/test_ci_changed_files.py`, `uv run ruff check .` → `All checks passed!`, `uv run python scripts/check_ownership.py --task W1-T14 --base origin/develop --branch HEAD` → no output, exit 0.

- [ ] **Step 2: Push and verify** (deferred to stage W1-S3, schedule YAML W1-T14 `deferred_steps: [2, 3]`) — after the W1-P3 integration PR has merged into `develop`, wait for the `push` run of `ci.yml` on that merge commit (`gh run watch "$(gh run list --branch develop --workflow ci.yml -L 1 --json databaseId --jq '.[0].databaseId')" --exit-status` → exit 0). Then run `gh api "repos/arkhash0309/rootline/commits/$(git rev-parse origin/develop)/check-runs" --jq '.check_runs[] | select(.name == "ci / required") | .conclusion'` → exactly one line `success` (PG-26, ADR 0045 D3). All other jobs are `success` or `skipped`. If the second command prints nothing, the job name does not match the ruleset context: the coordinator stops W1-S3 and sends W1-T14 back to its implementer on `feat/w1-ci-deferred`.

- [ ] **Step 3 [OWNER] (O-3): Create the rulesets on `rootline`** (GEN-020, deferred to stage W1-S3). Document the exact clicks in `wiki/runbooks/github-apps.md` § Rulesets, or run with confirmation:

```bash
gh api -X POST repos/arkhash0309/rootline/rulesets --input .github/rulesets/main.json
gh api -X POST repos/arkhash0309/rootline/rulesets --input .github/rulesets/develop.json
```

`.github/rulesets/main.json`: `{"name":"protect-main","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"deletion"},{"type":"non_fast_forward"},{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,"required_status_checks":[{"context":"ci / required"}]}}],"bypass_actors":[{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}]}` (actor 5 = repository admin role). `.github/rulesets/develop.json`: the same JSON with `"name":"protect-develop"`, `"include":["refs/heads/develop"]`, the same four rules in the same order, and no `bypass_actors` key. Both files are committed pretty-printed with 2-space indentation and a final newline. Neither file has a `required_linear_history` rule: it would reject the GEN-021 merge-commit release PR `develop → main`; GEN-021 wins because it is the more specific rule. The conflict is recorded in spec GEN-020 (row `main`, column "Protection", and the note below the table), spec §26 PG-26, ADR 0025 "Amendment 2026-11-27" and ADR 0045 D4.

Verification after the owner creates the rulesets (PG-26, ADR 0045 D3, D4):

| Command | Expected |
|---|---|
| `gh api repos/arkhash0309/rootline/rules/branches/develop --jq '.[] \| select(.type == "required_status_checks") \| .parameters.required_status_checks[].context'` | exactly one line `ci / required` |
| `gh api repos/arkhash0309/rootline/rules/branches/main --jq '.[] \| select(.type == "required_status_checks") \| .parameters.required_status_checks[].context'` | exactly one line `ci / required` |
| `gh api repos/arkhash0309/rootline/rules/branches/main --jq '[.[].type] \| sort \| join(",")'` | `deletion,non_fast_forward,pull_request,required_status_checks` |

If any command prints something else, the coordinator stops W1-S3 and asks the owner (O-3 is an **[OWNER]** step).

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
