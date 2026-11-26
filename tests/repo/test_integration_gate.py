"""Verifies PG-16 (overview §7.7 gate checks G1 to G11, report shape and exit codes), TST-002, TST-010."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts import integration_gate as gate
from scripts.integration_gate import CmdResult
from scripts.swarm_lib import load_schedule

REPO = Path(__file__).resolve().parents[2]
Rule = Callable[[list[str], Path], CmdResult | None]

REGISTRY_FILE = """id: TST-LAB-001
introduced_by: W2-T06
selectors:
  - {kind: pytest, target: "services/faultlab/tests/test_generate.py::test_tst_lab_001_counts"}
"""


class FakeRunner:
    """Records every command; the first rule that returns a result decides, otherwise exit 0."""

    def __init__(self, *rules: Rule) -> None:
        self.rules = rules
        self.calls: list[tuple[list[str], Path]] = []

    def __call__(self, cmd: object, cwd: Path, input_text: str | None = None) -> CmdResult:
        command = list(cmd)  # type: ignore[call-overload]
        self.calls.append((command, cwd))
        for rule in self.rules:
            result = rule(command, cwd)
            if result is not None:
                return result
        if "alembic" in command:
            return CmdResult(0, "0001_a (head)\n")
        if "--collect-only" in command:
            return CmdResult(0, "1 test collected in 0.1s\n")
        if "--write-regression" in command:
            committed = cwd / "eval/baselines/baseline-smoke.json"
            Path(command[command.index("--write-regression") + 1]).write_text(
                committed.read_text(encoding="utf-8"), encoding="utf-8"
            )
        return CmdResult(0, "ok\n")


def all_tools(name: str) -> str | None:
    return f"/usr/bin/{name}"


def touch(root: Path, rel: str, content: str = "x\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def full_tree(root: Path) -> None:
    """A checkout in which every optional input of G1 to G11 exists."""
    for rel in [
        "pyproject.toml",
        "apps/console/package.json",
        "scripts/render_versions.py",
        "scripts/check_contracts.py",
        "scripts/render_manifests.py",
        "scripts/wiki_lint.py",
        "services/agent/tests/test_prompts.py",
        "services/faultlab/tests/test_generate.py",
        "services/api/migrations/env.py",
        "services/api/alembic.ini",
        "services/api/tests/test_migrations.py",
        "policies/opa/rootline/policy.rego",
        "policies/kyverno/policy.yaml",
        "deploy/charts/rootline/Chart.yaml",
        "infra/terraform/persistent/main.tf",
        "libs/py-common/tests/test_a.py",
        "libs/py-common/rootline_common/__init__.py",
        "services/gate/tests/test_b.py",
        "services/gate/rootline_gate/__init__.py",
        "eval/baselines/baseline-smoke.json",
    ]:
        touch(root, rel)
    touch(root, "tests/registry/TST-LAB-001--W2-T06.yaml", REGISTRY_FILE)
    touch(
        root,
        "eval/baselines/baseline-smoke.json",
        json.dumps({"git_sha": "a", "results": {"s1": {"action": "x"}}}),
    )


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    branch = tmp_path / "branch"
    base = tmp_path / "base"
    branch.mkdir()
    base.mkdir()
    return branch, base


def run_gate(
    stage: str,
    dirs: tuple[Path, Path],
    runner: FakeRunner,
    *,
    pr_body: str = "",
    which: Callable[[str], str | None] = all_tools,
) -> list[gate.CheckResult]:
    branch_dir, base_dir = dirs
    return gate.run_checks(
        stage,
        "feat/x",
        "origin/develop",
        runner=runner,
        schedule=load_schedule(),
        workdir=branch_dir,
        base_workdir=base_dir,
        pr_body=pr_body,
        which=which,
        repo=REPO,
        base_sha="b" * 40,
        head_sha="h" * 40,
    )


def by_name(results: list[gate.CheckResult], name: str) -> gate.CheckResult:
    return next(r for r in results if r.name == name)


def test_checks_run_in_order_g1_to_g11(dirs: tuple[Path, Path]) -> None:
    full_tree(dirs[0])
    full_tree(dirs[1])
    results = run_gate("W1-P1", dirs, FakeRunner())
    groups = [int(r.name.split()[0][1:]) for r in results]
    assert groups == sorted(groups)
    assert set(groups) == set(range(1, 12))
    assert [r.status for r in results if r.status == "fail"] == []


def test_missing_input_is_a_skip_with_a_reason(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    results = run_gate("W1-P1", dirs, FakeRunner())
    console = by_name(results, "G6 console")
    assert (console.status, console.reason) == ("skip", "apps/console/package.json missing")
    assert by_name(results, "G10 replay").reason == "eval/baselines/baseline-smoke.json missing"
    assert by_name(results, "G11 wiki").reason == "scripts/wiki_lint.py missing"
    assert all(r.status in ("pass", "skip") for r in results)


def test_missing_tool_is_a_skip_with_a_reason(dirs: tuple[Path, Path]) -> None:
    full_tree(dirs[0])
    full_tree(dirs[1])
    results = run_gate(
        "W1-P1", dirs, FakeRunner(), which=lambda name: None if name == "npm" else f"/bin/{name}"
    )
    console = by_name(results, "G6 console")
    assert (console.status, console.reason) == ("skip", "npm not found on PATH")


def test_sequential_stage_skips_ownership(dirs: tuple[Path, Path]) -> None:
    full_tree(dirs[0])
    result = by_name(run_gate("W1-S1", dirs, FakeRunner()), "G1 ownership")
    assert (result.status, result.reason) == ("skip", "stage W1-S1 is sequential")


def test_ownership_runs_once_per_task_of_a_parallel_stage(dirs: tuple[Path, Path]) -> None:
    full_tree(dirs[0])
    runner = FakeRunner()
    run_gate("W1-P1", dirs, runner)
    ownership = [c for c, _ in runner.calls if "scripts/check_ownership.py" in c]
    assert [c[c.index("--task") + 1] for c in ownership] == ["W1-T02", "W1-T03"]
    assert all(
        c[c.index("--base") + 1] == "b" * 40 and c[c.index("--branch") + 1] == "h" * 40 for c in ownership
    )


def test_failing_command_fails_the_check_and_keeps_the_last_40_lines(dirs: tuple[Path, Path]) -> None:
    full_tree(dirs[0])
    lines = "\n".join(f"line {i}" for i in range(100))

    def fail_ruff(cmd: list[str], cwd: Path) -> CmdResult | None:
        return CmdResult(1, lines) if cmd[:4] == ["uv", "run", "ruff", "check"] else None

    results = run_gate("W1-S1", dirs, FakeRunner(fail_ruff))
    ruff = by_name(results, "G5 ruff")
    assert ruff.status == "fail"
    assert ruff.reason == "exit 1"
    assert ruff.output_tail.splitlines() == [f"line {i}" for i in range(60, 100)]
    assert gate.exit_code(results) == 1
    assert gate.exit_code([r for r in results if r.status != "fail"]) == 0


def test_unexpected_exception_in_a_check_is_a_fail(dirs: tuple[Path, Path]) -> None:
    full_tree(dirs[0])

    def boom(cmd: list[str], cwd: Path) -> CmdResult | None:
        if cmd[:3] == ["uv", "lock", "--locked"]:
            raise OSError("disk gone")
        return None

    result = by_name(run_gate("W1-S1", dirs, FakeRunner(boom)), "G2 uv-lock")
    assert result.status == "fail"
    assert "disk gone" in result.reason


def test_report_shape_and_report_only_exit_code(dirs: tuple[Path, Path], tmp_path: Path) -> None:
    full_tree(dirs[0])
    full_tree(dirs[1])

    def rev_parse(cmd: list[str], cwd: Path) -> CmdResult | None:
        return CmdResult(0, "c0ffee\n") if cmd[:2] == ["git", "rev-parse"] else None

    def fail_ruff(cmd: list[str], cwd: Path) -> CmdResult | None:
        return CmdResult(1, "bad\n") if cmd[:4] == ["uv", "run", "ruff", "check"] else None

    reports = tmp_path / "gates"
    common = {
        "schedule": load_schedule(),
        "workdir": dirs[0],
        "base_workdir": dirs[1],
        "report_dir": reports,
        "repo": REPO,
        "which": all_tools,
    }
    argv = ["--stage", "W1-S1", "--branch", "feat/x"]
    assert gate.main(argv, runner=FakeRunner(rev_parse, fail_ruff), **common) == 1  # type: ignore[arg-type]
    assert gate.main([*argv, "--report-only"], runner=FakeRunner(rev_parse, fail_ruff), **common) == 0  # type: ignore[arg-type]
    report = json.loads((reports / "W1-S1.json").read_text(encoding="utf-8"))
    assert set(report) == {"stage", "branch", "base_sha", "head_sha", "started_at", "checks"}
    assert (report["stage"], report["branch"]) == ("W1-S1", "feat/x")
    assert report["base_sha"] == report["head_sha"] == "c0ffee"
    assert report["started_at"].endswith("Z")
    assert set(report["checks"][0]) == {"name", "status", "reason", "duration_s", "output_tail"}
    assert {c["status"] for c in report["checks"]} <= {"pass", "fail", "skip"}
    assert any(c["name"] == "G5 ruff" and c["status"] == "fail" for c in report["checks"])
    assert gate.main(argv, runner=FakeRunner(rev_parse), **common) == 0  # type: ignore[arg-type]


def test_main_defaults_the_branch_to_the_integration_branch(dirs: tuple[Path, Path], tmp_path: Path) -> None:
    full_tree(dirs[0])
    reports = tmp_path / "gates"
    code = gate.main(
        ["--stage", "W1-P1", "--report-only"],
        runner=FakeRunner(),
        schedule=load_schedule(),
        workdir=dirs[0],
        base_workdir=dirs[1],
        report_dir=reports,
        repo=REPO,
        which=all_tools,
    )
    assert code == 0
    assert json.loads((reports / "W1-P1.json").read_text(encoding="utf-8"))["branch"] == "integration/w1-p1"


def test_g8_registry_file_removed_relative_to_base(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    touch(dirs[1], "tests/registry/TST-LAB-001--W2-T06.yaml", REGISTRY_FILE)
    failed = by_name(run_gate("W1-S1", dirs, FakeRunner()), "G8 registry")
    assert failed.status == "fail"
    assert "TST-LAB-001--W2-T06.yaml" in failed.reason
    exempt = run_gate(
        "W1-S1",
        dirs,
        FakeRunner(),
        pr_body="Summary\nregistry-removal: TST-LAB-001 superseded by TST-LAB-002\n",
    )
    assert by_name(exempt, "G8 registry").status == "pass"
    wrong_id = run_gate("W1-S1", dirs, FakeRunner(), pr_body="registry-removal: TST-LAB-002 other\n")
    assert by_name(wrong_id, "G8 registry").status == "fail"


def test_g8_rejects_an_invalid_registry_file_and_a_mismatching_file_name(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    touch(dirs[0], "tests/registry/TST-LAB-001--W2-T06.yaml", "id: TST-LAB-001\nintroduced_by: W2-T06\n")
    touch(dirs[0], "tests/registry/TST-LAB-002--W2-T06.yaml", REGISTRY_FILE)
    result = by_name(run_gate("W1-S1", dirs, FakeRunner()), "G8 registry")
    assert result.status == "fail"
    assert "TST-LAB-001--W2-T06.yaml" in result.reason
    assert "TST-LAB-002--W2-T06.yaml: file name must be TST-LAB-001--W2-T06.yaml" in result.reason


def test_g8_runs_each_selector_and_fails_when_none_is_collected(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    touch(dirs[0], "tests/registry/TST-LAB-001--W2-T06.yaml", REGISTRY_FILE)
    runner = FakeRunner()
    assert by_name(run_gate("W1-S1", dirs, runner), "G8 registry").status == "pass"
    selector = "services/faultlab/tests/test_generate.py::test_tst_lab_001_counts"
    assert (["uv", "run", "pytest", selector, "-q"], dirs[0]) in runner.calls

    def collects_nothing(cmd: list[str], cwd: Path) -> CmdResult | None:
        return CmdResult(5, "no tests ran\n") if selector in cmd else None

    failed = by_name(run_gate("W1-S1", dirs, FakeRunner(collects_nothing)), "G8 registry")
    assert failed.status == "fail"
    assert "collects no tests" in failed.reason


def test_g9_test_count_drop_needs_test_removal(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")

    def counts(cmd: list[str], cwd: Path) -> CmdResult | None:
        if "--collect-only" not in cmd:
            return None
        return CmdResult(
            0, "10 tests collected in 0.1s\n" if cwd == dirs[1] else "8 tests collected in 0.1s\n"
        )

    failed = by_name(run_gate("W1-S1", dirs, FakeRunner(counts)), "G9 test-count")
    assert failed.status == "fail"
    assert failed.reason == "collected tests dropped from 10 to 8"
    exempt = run_gate("W1-S1", dirs, FakeRunner(counts), pr_body="test-removal: duplicates merged\n")
    assert by_name(exempt, "G9 test-count").status == "pass"


def test_g9_equal_or_higher_count_passes(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")

    def counts(cmd: list[str], cwd: Path) -> CmdResult | None:
        if "--collect-only" not in cmd:
            return None
        return CmdResult(
            0, "10 tests collected in 0.1s\n" if cwd == dirs[1] else "11 tests collected in 0.1s\n"
        )

    assert by_name(run_gate("W1-S1", dirs, FakeRunner(counts)), "G9 test-count").status == "pass"


def baseline_writer(results: dict[str, dict[str, str]]) -> Rule:
    def rule(cmd: list[str], cwd: Path) -> CmdResult | None:
        if "--write-regression" not in cmd:
            return None
        out = Path(cmd[cmd.index("--write-regression") + 1])
        out.write_text(json.dumps({"git_sha": "new", "results": results}), encoding="utf-8")
        return CmdResult(0, "written\n")

    return rule


def test_g10_is_skipped_while_the_baseline_file_does_not_exist(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    result = by_name(run_gate("W1-S1", dirs, FakeRunner()), "G10 replay")
    assert (result.status, result.reason) == ("skip", "eval/baselines/baseline-smoke.json missing")


def test_g10_compares_predictions_exactly(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    committed = {"git_sha": "old", "results": {"s1": {"action": "x"}}}
    touch(dirs[0], "eval/baselines/baseline-smoke.json", json.dumps(committed))
    touch(dirs[1], "eval/baselines/baseline-smoke.json", json.dumps(committed))
    same = by_name(
        run_gate("W1-S1", dirs, FakeRunner(baseline_writer({"s1": {"action": "x"}}))), "G10 replay"
    )
    assert same.status == "pass"
    differs = by_name(
        run_gate("W1-S1", dirs, FakeRunner(baseline_writer({"s1": {"action": "y"}}))), "G10 replay"
    )
    assert differs.status == "fail"
    exempt_file_unchanged = run_gate(
        "W1-S1",
        dirs,
        FakeRunner(baseline_writer({"s1": {"action": "y"}})),
        pr_body="baseline-change: new prompt\n",
    )
    assert by_name(exempt_file_unchanged, "G10 replay").status == "fail"
    touch(
        dirs[0],
        "eval/baselines/baseline-smoke.json",
        json.dumps({"git_sha": "new", "results": {"s1": {"action": "y"}}}),
    )
    exempt = run_gate(
        "W1-S1",
        dirs,
        FakeRunner(baseline_writer({"s1": {"action": "y"}})),
        pr_body="baseline-change: new prompt\n",
    )
    assert by_name(exempt, "G10 replay").status == "pass"


def test_g11_runs_static_and_changed_files_rules(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    touch(dirs[0], "scripts/wiki_lint.py")
    runner = FakeRunner()
    assert by_name(run_gate("W1-S1", dirs, runner), "G11 wiki").status == "pass"
    wiki_calls = [c for c, _ in runner.calls if "scripts/wiki_lint.py" in c]
    assert len(wiki_calls) == 2
    assert "--changed-files" in wiki_calls[1] and "--pr-body" in wiki_calls[1]


def test_g7_runs_coverage_only_for_packages_with_tests(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    touch(dirs[0], "libs/py-common/tests/test_a.py")
    touch(dirs[0], "services/gate/tests/test_b.py")
    touch(dirs[0], "services/gate/rootline_gate/__init__.py")
    runner = FakeRunner()
    assert by_name(run_gate("W1-S1", dirs, runner), "G7 coverage").status == "pass"
    cov = [c for c, _ in runner.calls if any(a.startswith("--cov=") for a in c)]
    assert ["--cov=rootline_common" in c for c in cov].count(True) == 1
    assert any("--cov=rootline_gate" in c and "--cov-branch" in c and "--cov-fail-under=70" in c for c in cov)
    assert any("--cov=rootline_common" in c and "--cov-fail-under=80" in c for c in cov)
    assert not any("--cov=rootline_api" in c for c in cov)


def test_g7_is_skipped_without_package_tests(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    result = by_name(run_gate("W1-S1", dirs, FakeRunner()), "G7 coverage")
    assert (result.status, result.reason) == ("skip", "no Python package has tests")


def test_g4_requires_exactly_one_alembic_head(dirs: tuple[Path, Path]) -> None:
    touch(dirs[0], "pyproject.toml")
    touch(dirs[0], "services/api/migrations/env.py")
    touch(dirs[0], "services/api/alembic.ini")

    def heads(output: str) -> Rule:
        return lambda cmd, cwd: CmdResult(0, output) if "alembic" in cmd else None

    one = run_gate("W1-S1", dirs, FakeRunner(heads("0001_a (head)\n")))
    assert by_name(one, "G4 alembic-heads").status == "pass"
    two = run_gate("W1-S1", dirs, FakeRunner(heads("0001_a (head)\n0002_b (head)\n")))
    assert by_name(two, "G4 alembic-heads").status == "fail"
