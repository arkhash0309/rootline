"""task lint (W1-T06): run every linter whose inputs exist and print one summary line per step.

Exit code: 0 when every executed step passes, 1 when any step fails. A step whose trigger path does
not exist, or whose tool is not on PATH, is reported as `SKIP` and does not fail the run.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
STEP_TIMEOUT_S = 1800


@dataclass(frozen=True)
class Step:
    name: str
    cmd: list[str]
    needs: str | None  # repository-relative path that must exist, or None when always run
    pipe_from: list[str] | None = None  # command whose stdout is the stdin of `cmd`


def helm_charts() -> list[Path]:
    """Every directory under deploy/ that holds a Chart.yaml, excluding deploy/upstream (vendored)."""
    deploy = REPO / "deploy"
    if not deploy.is_dir():
        return []
    return sorted(
        p.parent for p in deploy.rglob("Chart.yaml") if "upstream" not in p.relative_to(deploy).parts
    )


def build_steps() -> list[Step]:
    steps = [
        Step("ruff check", ["uv", "run", "ruff", "check", "."], None),
        Step("ruff format", ["uv", "run", "ruff", "format", "--check", "."], None),
        Step("mypy", ["uv", "run", "mypy", "services", "libs", "eval/runner"], "libs"),
        Step("eslint", ["npm", "--prefix", "apps/console", "run", "lint"], "apps/console/package.json"),
        Step("tsc", ["npm", "--prefix", "apps/console", "run", "typecheck"], "apps/console/package.json"),
    ]
    for chart in helm_charts():
        rel = chart.relative_to(REPO).as_posix()
        steps.append(Step(f"helm lint {rel}", ["helm", "lint", rel], rel))
    steps.append(
        Step(
            "kubeconform",
            ["kubeconform", "-strict", "-summary", "-ignore-missing-schemas"],
            "scripts/render_manifests.py",
            pipe_from=["uv", "run", "python", "scripts/render_manifests.py"],
        )
    )
    steps.append(
        Step(
            "terraform fmt",
            ["terraform", "fmt", "-check", "-recursive", "infra/terraform"],
            "infra/terraform",
        )
    )
    steps.append(Step("tflint", ["tflint", "--recursive", "--chdir", "infra/terraform"], "infra/terraform"))
    return steps


def execute(step: Step) -> tuple[str, str]:
    """Return (status, detail) where status is OK, FAIL or SKIP."""
    if step.needs is not None and not (REPO / step.needs).exists():
        return "SKIP", f"{step.needs} missing"
    if shutil.which(step.cmd[0]) is None:
        return "SKIP", f"{step.cmd[0]} not on PATH"
    stdin: str | None = None
    if step.pipe_from is not None:
        rendered = run(step.pipe_from, check=False, timeout=STEP_TIMEOUT_S)
        if rendered.returncode != 0:
            return "FAIL", f"{' '.join(step.pipe_from)} exit {rendered.returncode}"
        stdin = rendered.stdout
    result = run(step.cmd, check=False, capture=False, timeout=STEP_TIMEOUT_S, input_text=stdin)
    return ("OK", "") if result.returncode == 0 else ("FAIL", f"exit {result.returncode}")


def main() -> int:
    failed = False
    for step in build_steps():
        status, detail = execute(step)
        print(f"{status:<4} {step.name}" + (f": {detail}" if detail else ""))
        failed = failed or status == "FAIL"
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
