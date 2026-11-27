"""task lint (GEN-060, W1-T06): run every linter whose inputs exist and print one summary line per step.

Per-step outcome, printed as one line `<STATUS> <step>[: <detail>]`:

- `OK`: the step ran and exited 0.
- `SKIP`: the step's input path does not exist (detail `<path> missing`). Not a failure.
- `FAIL`: the input path exists and the tool is not on PATH (detail `<tool> not on PATH`), or the tool
  exited non-zero (detail `exit <code>`), or the step ran longer than `STEP_TIMEOUT_S` (detail
  `timeout 1800 s`).

`STEP_TIMEOUT_S = 1800` is an implementation value (30 minutes per subprocess); the plan does not set it.
A timeout or a missing tool fails only its own step; the remaining steps still run.
Exit code: 0 when no step failed, 1 when any step failed.
"""

from __future__ import annotations

import shutil
import subprocess
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
    """Every directory under deploy/ that holds a Chart.yaml (no exclusions), sorted by path."""
    deploy = REPO / "deploy"
    if not deploy.is_dir():
        return []
    return sorted(p.parent for p in deploy.rglob("Chart.yaml"))


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
    """Return (status, detail), status being OK, FAIL or SKIP; a missing tool or a timeout does not raise."""
    if step.needs is not None and not (REPO / step.needs).exists():
        return "SKIP", f"{step.needs} missing"
    if shutil.which(step.cmd[0]) is None:
        return "FAIL", f"{step.cmd[0]} not on PATH"
    stdin: str | None = None
    try:
        if step.pipe_from is not None:
            if shutil.which(step.pipe_from[0]) is None:
                return "FAIL", f"{step.pipe_from[0]} not on PATH"
            rendered = run(step.pipe_from, check=False, timeout=STEP_TIMEOUT_S)
            if rendered.returncode != 0:
                return "FAIL", f"{' '.join(step.pipe_from)} exit {rendered.returncode}"
            stdin = rendered.stdout
        result = run(step.cmd, check=False, capture=False, timeout=STEP_TIMEOUT_S, input_text=stdin)
    except subprocess.TimeoutExpired:
        return "FAIL", f"timeout {STEP_TIMEOUT_S} s"
    except FileNotFoundError as exc:
        missing = exc.filename if isinstance(exc.filename, str) else step.cmd[0]
        return "FAIL", f"{missing} not on PATH"
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
