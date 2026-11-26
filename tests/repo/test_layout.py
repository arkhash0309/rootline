"""Verifies GEN-001, GEN-002, GEN-003, WIK-031."""
import importlib
import tomllib
from pathlib import Path

import pytest

DIRS = [
    ".claude/skills/rootline-wiki", ".github", "apps/console",
    "services/api", "services/agent", "services/gate", "services/faultlab",
    "services/mcp-k8s", "services/mcp-telemetry", "services/mcp-gitops",
    "libs/py-common", "libs/py-mcpkit", "libs/py-llm", "libs/py-schemas",
    "policies/opa", "policies/kyverno", "prompts", "eval/runner", "eval/baselines",
    "eval/reports", "deploy/root", "deploy/charts/rootline", "deploy/values",
    "deploy/upstream", "infra/terraform/persistent", "infra/terraform/cluster",
    "infra/k3d", "scripts", "docs/superpowers/specs", "docs/superpowers/plans",
    "docs/writeup", "wiki",
]
PACKAGES = [
    "rootline_api", "rootline_agent", "rootline_gate", "rootline_faultlab",
    "rootline_mcp_k8s", "rootline_mcp_telemetry", "rootline_mcp_gitops",
    "rootline_common", "rootline_mcpkit", "rootline_llm", "rootline_schemas", "rootline_eval",
]
ALLOWED_TOP_LEVEL = {
    ".claude", ".github", "apps", "services", "libs", "policies", "prompts", "eval",
    "deploy", "infra", "scripts", "docs", "wiki", "tests", "Taskfile.yml", "pyproject.toml",
    "uv.lock", "versions.yaml", "AGENTS.md", "CLAUDE.md", "README.md", "LICENSE",
    ".gitignore", ".gitattributes", ".env.example", ".git", ".venv", ".omc", ".superpowers",
    ".env.local", ".env.gke", "data", ".pytest_cache", ".ruff_cache", ".mypy_cache",
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
    for h in ["## Summary", "## Requirement IDs", "## Wiki pages updated", "## Tests",
              "## Screenshots (UI only)", "## Cost impact"]:
        assert h in text
