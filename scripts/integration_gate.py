"""Integration gate: checks G1 to G11 of overview §7.7 (G12 is `scripts/cluster_smoke.py`). PG-16.

Usage:
  uv run python scripts/integration_gate.py --stage <id> [--branch <ref>] [--base origin/develop]
      [--pr-body <file>] [--report-only]

Inputs:
  --stage        stage ID from the schedule, for example `W1-P1`. Required.
  --branch       ref to check. Default `integration/<stage id lowercase>`.
  --base         ref the branch is compared with. Default `origin/develop`.
  --pr-body      file holding the PR description; its lines `registry-removal: <TST-ID> <reason>`,
                 `test-removal: <reason>` and `baseline-change: <reason>` exempt G8, G9 and G10.
  --report-only  always exit 0; the report still records every `fail`.

Behaviour: the gate checks `--branch` out in a temporary worktree `.swarm/worktrees/<stage>` and the
base in `.swarm/worktrees/<stage>-base` (`git worktree add --detach`), runs `uv sync --all-packages
--frozen` in the branch worktree, runs every check, writes `.swarm/gates/<stage>.json`, and removes both
worktrees, so the coordinator's working tree is never modified. Each check is a function
`(ctx) -> CheckResult` with status `pass`, `fail` or `skip`; a check whose tool or input does not exist
is `skip` with the reason. The JSON report is `{stage, branch, base_sha, head_sha, started_at, checks}`;
`output_tail` is the last 40 output lines.

Exit codes: 0 no check failed (or `--report-only`); 1 at least one check failed or the worktree setup
failed; 2 unknown stage or unresolvable ref.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import jsonschema
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_ownership import always_allowed_ok, stage_offenders
from scripts.proc import run
from scripts.swarm_lib import REPO, Schedule, Stage, load_schedule

TAIL_LINES = 40
COMMAND_TIMEOUT_S = 3600

# Python import package -> package directory (GEN-002); TST-002 requires >= 80 % lines per package.
PACKAGE_DIRS: dict[str, str] = {
    "rootline_common": "libs/py-common",
    "rootline_mcpkit": "libs/py-mcpkit",
    "rootline_llm": "libs/py-llm",
    "rootline_schemas": "libs/py-schemas",
    "rootline_api": "services/api",
    "rootline_agent": "services/agent",
    "rootline_gate": "services/gate",
    "rootline_faultlab": "services/faultlab",
    "rootline_mcp_k8s": "services/mcp-k8s",
    "rootline_mcp_telemetry": "services/mcp-telemetry",
    "rootline_mcp_gitops": "services/mcp-gitops",
    "rootline_eval": "eval/runner",
}
# (coverage target, package directory); TST-002 requires >= 70 % branches for these.
BRANCH_TARGETS: list[tuple[str, str]] = [
    ("rootline_mcpkit.redact", "libs/py-mcpkit"),
    ("rootline_agent.guard", "services/agent"),
    ("rootline_api.auth", "services/api"),
    ("rootline_gate", "services/gate"),
]
LINE_COVERAGE_MIN = 80
BRANCH_COVERAGE_MIN = 70
BASELINE_FILE = "eval/baselines/baseline-smoke.json"


@dataclass
class CmdResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class Runner(Protocol):
    def __call__(self, cmd: Sequence[str], cwd: Path, input_text: str | None = None) -> CmdResult: ...


Which = Callable[[str], str | None]


@dataclass
class CheckResult:
    name: str
    status: str
    reason: str = ""
    duration_s: float = 0.0
    output_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_runner(cmd: Sequence[str], cwd: Path, input_text: str | None = None) -> CmdResult:
    """Run `cmd` in `cwd` through `scripts.proc.run` (`env --chdir` because `run` has no cwd argument)."""
    try:
        done = run(
            ["env", "--chdir", str(cwd), *cmd], check=False, timeout=COMMAND_TIMEOUT_S, input_text=input_text
        )
    except subprocess.TimeoutExpired:
        return CmdResult(124, "", f"timeout after {COMMAND_TIMEOUT_S} s: {' '.join(cmd)}\n")
    return CmdResult(done.returncode, done.stdout or "", done.stderr or "")


def tail(text: str) -> str:
    return "\n".join(text.splitlines()[-TAIL_LINES:])


@dataclass
class GateContext:
    stage: Stage
    schedule: Schedule
    branch: str
    base: str
    base_sha: str
    head_sha: str
    workdir: Path
    base_workdir: Path | None
    repo: Path
    pr_body: str
    runner: Runner
    which: Which

    def run(self, cmd: Sequence[str], cwd: Path | None = None, input_text: str | None = None) -> CmdResult:
        return self.runner(list(cmd), cwd or self.workdir, input_text)

    def exists(self, rel: str) -> bool:
        return (self.workdir / rel).exists()

    def has_files(self, rel_dir: str, pattern: str = "*") -> bool:
        directory = self.workdir / rel_dir
        return directory.is_dir() and any(
            p.is_file() and p.name != ".gitkeep" for p in directory.rglob(pattern)
        )

    def exemption(self, key: str, argument: str | None = None) -> bool:
        """True when the PR body has a line `<key>: <argument> <reason>` (or `<key>: <reason>`)."""
        prefix = re.escape(key + ":") + (r" " + re.escape(argument) if argument else "")
        return re.search(rf"^{prefix} \S.*$", self.pr_body, re.M) is not None


def skip(name: str, reason: str) -> CheckResult:
    return CheckResult(name, "skip", reason)


def command_check(
    ctx: GateContext,
    name: str,
    cmd: Sequence[str],
    *,
    requires: Sequence[str] = (),
    tool: str | None = None,
    cwd: Path | None = None,
) -> CheckResult:
    """Run one command; `requires` are checkout-relative inputs that must exist, `tool` must be on PATH."""
    for rel in requires:
        if not ctx.exists(rel):
            return skip(name, f"{rel} missing")
    executable = tool or cmd[0]
    if ctx.which(executable) is None:
        return skip(name, f"{executable} not found on PATH")
    result = ctx.run(cmd, cwd)
    if result.returncode == 0:
        return CheckResult(name, "pass", "", 0.0, tail(result.output))
    return CheckResult(name, "fail", f"exit {result.returncode}", 0.0, tail(result.output))


def aggregate(
    name: str, outcomes: list[tuple[str, CmdResult]], ok: Callable[[CmdResult], bool]
) -> CheckResult:
    """One CheckResult from several commands: fail when `ok` is false for any of them."""
    failed = [(label, result) for label, result in outcomes if not ok(result)]
    if not failed:
        return CheckResult(name, "pass")
    reason = "; ".join(f"{label}: exit {result.returncode}" for label, result in failed)
    return CheckResult(name, "fail", reason, 0.0, tail(failed[-1][1].output))


# ---- G1 ownership -------------------------------------------------------------------------------


def g1_ownership(ctx: GateContext) -> CheckResult:
    """G1 on an integration branch (overview §7.4 and §7.7).

    Every path in `git diff --name-only --no-renames -z <base>...<head>` MUST be owned (`owns` minus
    `excludes`) by at least one task of the stage, or match `always_allowed` and satisfy that path's
    special rule. The rule is `scripts.check_ownership.stage_offenders`, the same function the CLI
    `scripts/check_ownership.py --stage` uses (ADR 0040 item 7). A task is never blamed for a sibling's
    files; the per-task check on a task branch is `scripts/check_ownership.py --task`.
    """
    name = "G1 ownership"
    if ctx.stage.mode != "parallel":
        return skip(name, f"stage {ctx.stage.id} is sequential")
    diff = ctx.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", f"{ctx.base_sha}...{ctx.head_sha}"], ctx.repo
    )
    if diff.returncode != 0:
        return CheckResult(name, "fail", f"git diff exit {diff.returncode}", 0.0, tail(diff.output))
    paths = [path for path in diff.stdout.split("\0") if path]
    if not paths:
        return CheckResult(name, "pass", "no changed paths")
    merge_base = ctx.run(["git", "merge-base", ctx.base_sha, ctx.head_sha], ctx.repo)
    if merge_base.returncode != 0:
        return CheckResult(
            name, "fail", f"git merge-base exit {merge_base.returncode}", 0.0, tail(merge_base.output)
        )

    def read(ref: str, path: str) -> str | None:
        shown = ctx.run(["git", "show", f"{ref}:{path}"], ctx.repo)
        return shown.stdout if shown.returncode == 0 else None

    offenders = stage_offenders(
        ctx.schedule,
        ctx.stage,
        paths,
        lambda path: always_allowed_ok(ctx.repo, path, merge_base.stdout.strip(), ctx.head_sha, read),
    )
    if offenders:
        return CheckResult(name, "fail", "; ".join(offenders), 0.0, tail("\n".join(offenders)))
    return CheckResult(name, "pass")


# ---- G2 lockfiles -------------------------------------------------------------------------------


def g2_uv_lock(ctx: GateContext) -> CheckResult:
    return command_check(ctx, "G2 uv-lock", ["uv", "lock", "--locked"], requires=["pyproject.toml"])


def g2_npm_ci(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx,
        "G2 npm-ci",
        ["npm", "--prefix", "apps/console", "ci", "--dry-run"],
        requires=["apps/console/package.json"],
    )


# ---- G3 generated files ---------------------------------------------------------------------------


def g3_versions(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx,
        "G3 versions",
        ["uv", "run", "python", "scripts/render_versions.py", "--check"],
        requires=["scripts/render_versions.py"],
    )


def g3_contracts(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx,
        "G3 contracts",
        ["uv", "run", "python", "scripts/check_contracts.py"],
        requires=["scripts/check_contracts.py"],
    )


def g3_prompt_hashes(ctx: GateContext) -> CheckResult:
    test = "services/agent/tests/test_prompts.py"
    return command_check(ctx, "G3 prompt-hashes", ["uv", "run", "pytest", test, "-q"], requires=[test])


def g3_scenarios(ctx: GateContext) -> CheckResult:
    test = "services/faultlab/tests/test_generate.py"
    return command_check(ctx, "G3 scenarios", ["uv", "run", "pytest", test, "-q"], requires=[test])


# ---- G4 migrations --------------------------------------------------------------------------------


def g4_alembic_heads(ctx: GateContext) -> CheckResult:
    name = "G4 alembic-heads"
    if not ctx.exists("services/api/migrations"):
        return skip(name, "services/api/migrations missing")
    if not ctx.exists("services/api/alembic.ini"):
        return skip(name, "services/api/alembic.ini missing")
    if ctx.which("uv") is None:
        return skip(name, "uv not found on PATH")
    result = ctx.run(["uv", "run", "alembic", "-c", "services/api/alembic.ini", "heads"])
    heads = len(re.findall(r"\(head\)", result.output))
    if result.returncode != 0:
        return CheckResult(name, "fail", f"exit {result.returncode}", 0.0, tail(result.output))
    if heads != 1:
        return CheckResult(
            name, "fail", f"{heads} Alembic heads, expected exactly 1", 0.0, tail(result.output)
        )
    return CheckResult(name, "pass", "", 0.0, tail(result.output))


def g4_migrations(ctx: GateContext) -> CheckResult:
    test = "services/api/tests/test_migrations.py"
    if not ctx.exists("services/api/migrations"):
        return skip("G4 migrations-test", "services/api/migrations missing")
    return command_check(ctx, "G4 migrations-test", ["uv", "run", "pytest", test, "-q"], requires=[test])


# ---- G5 static ------------------------------------------------------------------------------------


def g5_ruff(ctx: GateContext) -> CheckResult:
    return command_check(ctx, "G5 ruff", ["uv", "run", "ruff", "check", "."], requires=["pyproject.toml"])


def g5_ruff_format(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx, "G5 ruff-format", ["uv", "run", "ruff", "format", "--check", "."], requires=["pyproject.toml"]
    )


def g5_mypy(ctx: GateContext) -> CheckResult:
    name = "G5 mypy"
    if not any(ctx.has_files(d, "*.py") for d in ("services", "libs", "eval/runner")):
        return skip(name, "no Python files under services, libs or eval/runner")
    return command_check(ctx, name, ["uv", "run", "mypy", "services", "libs", "eval/runner"])


def g5_eslint(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx,
        "G5 eslint",
        ["npm", "--prefix", "apps/console", "run", "lint"],
        requires=["apps/console/package.json"],
    )


def g5_tsc(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx,
        "G5 tsc",
        ["npm", "--prefix", "apps/console", "run", "typecheck"],
        requires=["apps/console/package.json"],
    )


def g5_helm_lint(ctx: GateContext) -> CheckResult:
    name = "G5 helm-lint"
    charts = sorted(
        p.parent.relative_to(ctx.workdir).as_posix() for p in (ctx.workdir / "deploy").rglob("Chart.yaml")
    )
    if not charts:
        return skip(name, "no Chart.yaml under deploy")
    if ctx.which("helm") is None:
        return skip(name, "helm not found on PATH")
    return aggregate(name, [(c, ctx.run(["helm", "lint", c])) for c in charts], lambda r: r.returncode == 0)


def g5_kubeconform(ctx: GateContext) -> CheckResult:
    name = "G5 kubeconform"
    if not ctx.exists("scripts/render_manifests.py"):
        return skip(name, "scripts/render_manifests.py missing")
    for tool in ("uv", "kubeconform"):
        if ctx.which(tool) is None:
            return skip(name, f"{tool} not found on PATH")
    rendered = ctx.run(["uv", "run", "python", "scripts/render_manifests.py"])
    if rendered.returncode != 0:
        return CheckResult(
            name, "fail", f"render_manifests.py exit {rendered.returncode}", 0.0, tail(rendered.output)
        )
    checked = ctx.run(
        ["kubeconform", "-strict", "-summary", "-ignore-missing-schemas"], input_text=rendered.stdout
    )
    if checked.returncode != 0:
        return CheckResult(name, "fail", f"exit {checked.returncode}", 0.0, tail(checked.output))
    return CheckResult(name, "pass", "", 0.0, tail(checked.output))


def terraform_modules(ctx: GateContext) -> list[str]:
    root = ctx.workdir / "infra/terraform"
    if not root.is_dir():
        return []
    return sorted(
        d.relative_to(ctx.workdir).as_posix() for d in root.iterdir() if d.is_dir() and any(d.glob("*.tf"))
    )


def g5_terraform_fmt(ctx: GateContext) -> CheckResult:
    modules = terraform_modules(ctx)
    if not modules:
        return skip("G5 terraform-fmt", "no .tf files under infra/terraform")
    return command_check(
        ctx, "G5 terraform-fmt", ["terraform", "fmt", "-check", "-recursive", "infra/terraform"]
    )


def g5_terraform_validate(ctx: GateContext) -> CheckResult:
    name = "G5 terraform-validate"
    modules = terraform_modules(ctx)
    if not modules:
        return skip(name, "no .tf files under infra/terraform")
    if ctx.which("terraform") is None:
        return skip(name, "terraform not found on PATH")
    outcomes: list[tuple[str, CmdResult]] = []
    for module in modules:
        init = ctx.run(["terraform", f"-chdir={module}", "init", "-backend=false", "-input=false"])
        outcomes.append((f"{module} init", init))
        if init.returncode == 0:
            outcomes.append((f"{module} validate", ctx.run(["terraform", f"-chdir={module}", "validate"])))
    return aggregate(name, outcomes, lambda r: r.returncode == 0)


def g5_tflint(ctx: GateContext) -> CheckResult:
    if not terraform_modules(ctx):
        return skip("G5 tflint", "no .tf files under infra/terraform")
    return command_check(ctx, "G5 tflint", ["tflint", "--recursive", "--chdir", "infra/terraform"])


def g5_opa_fmt(ctx: GateContext) -> CheckResult:
    if not ctx.has_files("policies/opa", "*.rego"):
        return skip("G5 opa-fmt", "policies/opa has no .rego files")
    return command_check(ctx, "G5 opa-fmt", ["opa", "fmt", "--diff", "--fail", "policies/opa"])


# ---- G6 unit and integration tests ---------------------------------------------------------------


def g6_pytest(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx, "G6 pytest", ["uv", "run", "pytest", "-m", "not k8s"], requires=["pyproject.toml"]
    )


def g6_console(ctx: GateContext) -> CheckResult:
    return command_check(
        ctx,
        "G6 console",
        ["npm", "--prefix", "apps/console", "run", "test", "--", "--run"],
        requires=["apps/console/package.json"],
    )


def g6_opa(ctx: GateContext) -> CheckResult:
    if not ctx.has_files("policies/opa", "*.rego"):
        return skip("G6 opa", "policies/opa has no .rego files")
    return command_check(ctx, "G6 opa", ["opa", "test", "policies/opa"])


def g6_kyverno(ctx: GateContext) -> CheckResult:
    if not ctx.has_files("policies/kyverno"):
        return skip("G6 kyverno", "policies/kyverno has no files")
    return command_check(ctx, "G6 kyverno", ["kyverno", "test", "policies/kyverno"])


# ---- G7 coverage ----------------------------------------------------------------------------------


def _target_exists(ctx: GateContext, directory: str, target: str) -> bool:
    base = Path(directory) / target.replace(".", "/")
    return ctx.exists(base.as_posix()) or ctx.exists(base.as_posix() + ".py")


def g7_coverage(ctx: GateContext) -> CheckResult:
    name = "G7 coverage"
    runs: list[tuple[str, list[str]]] = []
    for package, directory in PACKAGE_DIRS.items():
        if not ctx.has_files(f"{directory}/tests", "test_*.py"):
            continue
        runs.append(
            (
                f"{package} lines",
                [
                    "uv",
                    "run",
                    "pytest",
                    f"{directory}/tests",
                    "-m",
                    "not k8s",
                    "-q",
                    f"--cov={package}",
                    f"--cov-fail-under={LINE_COVERAGE_MIN}",
                ],
            )
        )
    for target, directory in BRANCH_TARGETS:
        if ctx.has_files(f"{directory}/tests", "test_*.py") and _target_exists(ctx, directory, target):
            runs.append(
                (
                    f"{target} branches",
                    [
                        "uv",
                        "run",
                        "pytest",
                        f"{directory}/tests",
                        "-m",
                        "not k8s",
                        "-q",
                        f"--cov={target}",
                        "--cov-branch",
                        f"--cov-fail-under={BRANCH_COVERAGE_MIN}",
                    ],
                )
            )
    if not runs:
        return skip(name, "no Python package has tests")
    if ctx.which("uv") is None:
        return skip(name, "uv not found on PATH")
    return aggregate(name, [(label, ctx.run(cmd)) for label, cmd in runs], lambda r: r.returncode == 0)


# ---- G8 named-test registry -----------------------------------------------------------------------


def _registry_schema(ctx: GateContext) -> dict[str, Any]:
    for root in (ctx.workdir, ctx.repo):
        path = root / "tests/registry/schema.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    return {}


def _selector_command(kind: str, target: str) -> list[str] | None:
    if kind == "pytest":
        return ["uv", "run", "pytest", target, "-q"]
    if kind == "vitest":
        return ["npm", "--prefix", "apps/console", "run", "test", "--", "--run", target]
    if kind == "opa":
        return ["opa", "test", target]
    if kind == "kyverno":
        return ["kyverno", "test", target]
    return None  # playwright entries are listed, executed only by e2e.yml and W6-T10


def g8_registry(ctx: GateContext) -> CheckResult:
    name = "G8 registry"
    registry = ctx.workdir / "tests/registry"
    base_registry = ctx.base_workdir / "tests/registry" if ctx.base_workdir else None
    base_files = (
        sorted(p.name for p in base_registry.glob("*.yaml"))
        if base_registry and base_registry.is_dir()
        else []
    )
    if not registry.is_dir() and not base_files:
        return skip(name, "tests/registry missing")
    files = sorted(registry.glob("*.yaml")) if registry.is_dir() else []
    problems: list[str] = []
    last_output = ""
    for removed in sorted(set(base_files) - {p.name for p in files}):
        test_id = removed.split("--")[0]
        if not ctx.exemption("registry-removal", test_id):
            problems.append(
                f"{removed}: registry file removed without `registry-removal: {test_id} <reason>`"
            )
    validator = jsonschema.Draft202012Validator(_registry_schema(ctx))
    runnable: list[tuple[str, str, str]] = []
    for path in files:
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            problems.append(f"{path.name}: invalid YAML: {error}")
            continue
        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        if errors:
            problems.append(f"{path.name}: {errors[0].message}")
            continue
        expected = f"{document['id']}--{document['introduced_by']}.yaml"
        if path.name != expected:
            problems.append(f"{path.name}: file name must be {expected}")
        for selector in document["selectors"]:
            runnable.append((path.name, selector["kind"], selector["target"]))
    for file_name, kind, target in runnable:
        cmd = _selector_command(kind, target)
        if cmd is None:
            continue
        if ctx.which(cmd[0]) is None:
            problems.append(f"{file_name}: {cmd[0]} not found on PATH for {kind} selector {target}")
            continue
        result = ctx.run(cmd)
        if result.returncode == 5 and kind == "pytest":
            problems.append(f"{file_name}: selector {target} collects no tests")
            last_output = result.output
        elif result.returncode != 0:
            problems.append(f"{file_name}: selector {target} exit {result.returncode}")
            last_output = result.output
    if problems:
        return CheckResult(name, "fail", "; ".join(problems), 0.0, tail(last_output))
    return CheckResult(name, "pass")


# ---- G9 no test loss ------------------------------------------------------------------------------

COLLECTED_RE = re.compile(r"(\d+) tests? collected")


def count_tests(output: str) -> int | None:
    match = COLLECTED_RE.search(output)
    if match:
        return int(match.group(1))
    ids = [line for line in output.splitlines() if "::" in line]
    return len(ids) if ids else None


def _collected(result: CmdResult) -> int | None:
    """Collected test count; pytest exit code 5 means zero tests; None means collection failed."""
    if result.returncode == 5:
        return 0
    if result.returncode != 0:
        return None
    return count_tests(result.output)


def g9_test_count(ctx: GateContext) -> CheckResult:
    name = "G9 test-count"
    if ctx.base_workdir is None:
        return skip(name, "base checkout not available")
    if ctx.which("uv") is None:
        return skip(name, "uv not found on PATH")
    cmd = ["uv", "run", "pytest", "--collect-only", "-q"]
    branch = ctx.run(cmd, ctx.workdir)
    base = ctx.run(cmd, ctx.base_workdir)
    branch_count = _collected(branch)
    base_count = _collected(base)
    if branch_count is None:
        return CheckResult(name, "fail", "test collection failed on the branch", 0.0, tail(branch.output))
    if base_count is None:
        return CheckResult(name, "fail", "test collection failed on the base", 0.0, tail(base.output))
    if branch_count < base_count and not ctx.exemption("test-removal"):
        return CheckResult(
            name,
            "fail",
            f"collected tests dropped from {base_count} to {branch_count}",
            0.0,
            tail(branch.output),
        )
    return CheckResult(name, "pass", f"{base_count} on the base, {branch_count} on the branch")


# ---- G10 replay regression ------------------------------------------------------------------------


def _baseline_results(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")).get("results")


def g10_replay(ctx: GateContext) -> CheckResult:
    name = "G10 replay"
    committed = ctx.workdir / BASELINE_FILE
    if not committed.is_file():
        return skip(name, f"{BASELINE_FILE} missing")
    if ctx.which("uv") is None:
        return skip(name, "uv not found on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "baseline-smoke.json"
        result = ctx.run(
            ["uv", "run", "rootline-eval", "baseline", "--split", "smoke", "--write-regression", str(out)]
        )
        if result.returncode != 0 or not out.is_file():
            return CheckResult(
                name, "fail", f"rootline-eval baseline exit {result.returncode}", 0.0, tail(result.output)
            )
        produced = _baseline_results(out)
    if produced == _baseline_results(committed):
        return CheckResult(name, "pass")
    if ctx.exemption("baseline-change"):
        base_file = ctx.base_workdir / BASELINE_FILE if ctx.base_workdir else None
        updated = (
            base_file is None
            or not base_file.is_file()
            or committed.read_text(encoding="utf-8") != base_file.read_text(encoding="utf-8")
        )
        if updated:
            return CheckResult(name, "pass", "baseline-change exemption; baseline file updated in this PR")
        return CheckResult(
            name, "fail", "baseline-change given but the baseline file is not updated in this PR"
        )
    return CheckResult(
        name, "fail", "smoke predictions differ from the committed baseline", 0.0, tail(result.output)
    )


# ---- G11 wiki -------------------------------------------------------------------------------------


def g11_wiki(ctx: GateContext) -> CheckResult:
    name = "G11 wiki"
    if not ctx.exists("scripts/wiki_lint.py"):
        return skip(name, "scripts/wiki_lint.py missing")
    if ctx.which("uv") is None:
        return skip(name, "uv not found on PATH")
    static = ctx.run(["uv", "run", "python", "scripts/wiki_lint.py"])
    with tempfile.TemporaryDirectory() as tmp:
        diff = ctx.run(["git", "diff", "--name-only", f"{ctx.base_sha}...{ctx.head_sha}"], ctx.repo)
        changed = Path(tmp) / "changed.txt"
        changed.write_text(diff.stdout, encoding="utf-8")
        body = Path(tmp) / "body.txt"
        body.write_text(ctx.pr_body, encoding="utf-8")
        rule = ctx.run(
            [
                "uv",
                "run",
                "python",
                "scripts/wiki_lint.py",
                "--changed-files",
                str(changed),
                "--pr-body",
                str(body),
            ]
        )
    return aggregate(name, [("static", static), ("changed-files", rule)], lambda r: r.returncode == 0)


CHECKS: list[Callable[[GateContext], CheckResult]] = [
    g1_ownership,
    g2_uv_lock,
    g2_npm_ci,
    g3_versions,
    g3_contracts,
    g3_prompt_hashes,
    g3_scenarios,
    g4_alembic_heads,
    g4_migrations,
    g5_ruff,
    g5_ruff_format,
    g5_mypy,
    g5_eslint,
    g5_tsc,
    g5_helm_lint,
    g5_kubeconform,
    g5_terraform_fmt,
    g5_terraform_validate,
    g5_tflint,
    g5_opa_fmt,
    g6_pytest,
    g6_console,
    g6_opa,
    g6_kyverno,
    g7_coverage,
    g8_registry,
    g9_test_count,
    g10_replay,
    g11_wiki,
]


def _check_label(check: Callable[[GateContext], CheckResult]) -> str:
    """`g2_uv_lock` becomes `G2 uv-lock`."""
    group, _, rest = check.__name__.partition("_")
    return f"{group.upper()} {rest.replace('_', '-')}"


def run_checks(
    stage: str,
    branch: str,
    base: str,
    *,
    runner: Runner | None = None,
    schedule: Schedule | None = None,
    workdir: Path | None = None,
    base_workdir: Path | None = None,
    pr_body: str = "",
    which: Which | None = None,
    repo: Path | None = None,
    base_sha: str | None = None,
    head_sha: str | None = None,
) -> list[CheckResult]:
    """Run G1 to G11 in order against the checkout in `workdir`. Raises KeyError for an unknown stage."""
    sched = schedule or load_schedule()
    stage_entry = sched.get_stage(stage)
    if stage_entry is None:
        raise KeyError(stage)
    ctx = GateContext(
        stage=stage_entry,
        schedule=sched,
        branch=branch,
        base=base,
        base_sha=base_sha or base,
        head_sha=head_sha or branch,
        workdir=workdir or REPO,
        base_workdir=base_workdir,
        repo=repo or REPO,
        pr_body=pr_body,
        runner=runner or default_runner,
        which=which or shutil.which,
    )
    results: list[CheckResult] = []
    for check in CHECKS:
        started = time.monotonic()
        try:
            result = check(ctx)
        except Exception as error:  # a crashing check is reported as a fail, never swallowed
            result = CheckResult(_check_label(check), "fail", f"internal error: {error!r}")
        result.duration_s = round(time.monotonic() - started, 3)
        results.append(result)
    return results


def exit_code(results: Sequence[CheckResult]) -> int:
    return 1 if any(r.status == "fail" for r in results) else 0


def build_report(
    stage: str, branch: str, base_sha: str, head_sha: str, started_at: str, results: Sequence[CheckResult]
) -> dict[str, Any]:
    return {
        "stage": stage,
        "branch": branch,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "started_at": started_at,
        "checks": [r.to_dict() for r in results],
    }


def _resolve(runner: Runner, repo: Path, ref: str) -> str | None:
    result = runner(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], repo)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def _remove_worktree(runner: Runner, repo: Path, path: Path) -> None:
    runner(["git", "worktree", "remove", "--force", str(path)], repo)
    runner(["git", "worktree", "prune"], repo)


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner | None = None,
    which: Which | None = None,
    schedule: Schedule | None = None,
    workdir: Path | None = None,
    base_workdir: Path | None = None,
    report_dir: Path | None = None,
    repo: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--stage", required=True)
    parser.add_argument("--branch")
    parser.add_argument("--base", default="origin/develop")
    parser.add_argument("--pr-body")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)
    run_ = runner or default_runner
    repo_dir = repo or REPO
    sched = schedule or load_schedule()
    stage = sched.get_stage(args.stage)
    if stage is None:
        print(f"unknown stage: {args.stage}", file=sys.stderr)
        return 2
    branch = args.branch or f"integration/{stage.id.lower()}"
    pr_body = Path(args.pr_body).read_text(encoding="utf-8") if args.pr_body else ""
    base_sha, head_sha = _resolve(run_, repo_dir, args.base), _resolve(run_, repo_dir, branch)
    if base_sha is None or head_sha is None:
        print(
            f"cannot resolve {'base ' + args.base if base_sha is None else 'branch ' + branch}",
            file=sys.stderr,
        )
        return 2
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    created: list[Path] = []
    results: list[CheckResult]
    try:
        if workdir is None:
            branch_dir = repo_dir / ".swarm/worktrees" / stage.id
            base_dir = repo_dir / ".swarm/worktrees" / f"{stage.id}-base"
            try:
                for path, sha in ((branch_dir, head_sha), (base_dir, base_sha)):
                    _remove_worktree(run_, repo_dir, path)
                    added = run_(["git", "worktree", "add", "--detach", str(path), sha], repo_dir)
                    if added.returncode != 0:
                        raise RuntimeError(f"git worktree add {path} failed: {added.stderr.strip()}")
                    created.append(path)
            except RuntimeError as error:
                results = [CheckResult("setup worktree", "fail", str(error))]
            else:
                synced = run_(["uv", "sync", "--all-packages", "--frozen"], branch_dir)
                if synced.returncode != 0:
                    results = [
                        CheckResult(
                            "setup uv-sync", "fail", f"exit {synced.returncode}", 0.0, tail(synced.output)
                        )
                    ]
                else:
                    results = run_checks(
                        stage.id,
                        branch,
                        args.base,
                        runner=run_,
                        schedule=sched,
                        workdir=branch_dir,
                        base_workdir=base_dir,
                        pr_body=pr_body,
                        which=which,
                        repo=repo_dir,
                        base_sha=base_sha,
                        head_sha=head_sha,
                    )
        else:
            results = run_checks(
                stage.id,
                branch,
                args.base,
                runner=run_,
                schedule=sched,
                workdir=workdir,
                base_workdir=base_workdir,
                pr_body=pr_body,
                which=which,
                repo=repo_dir,
                base_sha=base_sha,
                head_sha=head_sha,
            )
    finally:
        for path in created:
            _remove_worktree(run_, repo_dir, path)
    report = build_report(stage.id, branch, base_sha, head_sha, started_at, results)
    directory = report_dir or repo_dir / ".swarm/gates"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stage.id}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(f"{r.status.upper():4} {r.name}" + (f": {r.reason}" if r.reason else ""))
    code = exit_code(results)
    print(
        f"gate {stage.id}: {'FAIL' if code else 'OK'} ({sum(r.status == 'fail' for r in results)} fail, "
        f"{sum(r.status == 'skip' for r in results)} skip, {sum(r.status == 'pass' for r in results)} pass)"
    )
    return 0 if args.report_only else code


if __name__ == "__main__":
    raise SystemExit(main())
