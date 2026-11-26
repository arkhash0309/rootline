"""Verifies PG-16 (overview §7.2 rules)."""

from pathlib import Path

import pytest

from scripts import swarm_lib, swarm_schedule
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
    bad.write_text(
        """
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
          - id: W9-T02
            branch: feat/b
            owns: [a/b.py, services/api/migrations/versions/0010_y.py]
            deferred_steps: [2]
""",
        encoding="utf-8",
    )
    errors = validate_schedule(load_schedule(bad))
    assert "W9-P1: unknown stage in after: W9-X" in errors
    assert "W9-P1: W9-T01 and W9-T02 both own a/b.py" in errors
    assert "W9-P1: two tasks add Alembic revisions" in errors
    assert "W9-P1: W9-T02 has deferred_steps but no deferred_to" in errors


def test_matches_gitignore_style() -> None:
    assert matches("services/api/x/y.py", ["services/api/**"])
    assert matches("apps/console/app/(app)/lab/page.tsx", ["apps/console/app/(app)/lab/**"])
    assert not matches("services/apix/y.py", ["services/api/**"])


def test_pattern_without_slash_is_anchored_at_the_root() -> None:
    """Verifies PG-16: `versions.yaml` owns the root file only, not `deploy/root/files/versions.yaml`."""
    assert matches("versions.yaml", ["versions.yaml"])
    assert not matches("deploy/root/files/versions.yaml", ["versions.yaml"])
    assert matches("libs/py-common/pyproject.toml", ["**/pyproject.toml"])


def write_schedule(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "s.yaml"
    path.write_text(
        "version: 1\nmax_parallel_implementers: 3\nalways_allowed: []\nweeks:\n" + body, encoding="utf-8"
    )
    return path


def test_stage_id_format_and_uniqueness(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - {id: W9-S1, mode: sequential, after: [], tasks: [{id: W9-T01, branch: feat/a}]}
      - {id: W9-S1, mode: sequential, after: [], tasks: [{id: W9-T02, branch: feat/b}]}
      - {id: W9-X1, mode: sequential, after: [], tasks: [{id: W9-T03, branch: feat/c}]}
""",
    )
    errors = validate_schedule(load_schedule(path))
    assert "W9-S1: duplicate stage id" in errors
    assert "W9-X1: stage id does not match ^W\\d-[SP]\\d$" in errors


def test_after_must_reference_an_earlier_stage(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - {id: W9-S1, mode: sequential, after: [W9-S2], tasks: [{id: W9-T01, branch: feat/a}]}
      - {id: W9-S2, mode: sequential, after: [], tasks: [{id: W9-T02, branch: feat/b}]}
""",
    )
    assert "W9-S1: stage in after is not earlier: W9-S2" in validate_schedule(load_schedule(path))


def test_parallel_task_needs_branch_and_owns(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - id: W9-P1
        mode: parallel
        after: []
        tasks:
          - {id: W9-T01, branch: null, owns: [a/**]}
          - {id: W9-T02, branch: feat/b}
""",
    )
    errors = validate_schedule(load_schedule(path))
    assert "W9-P1: W9-T01 has no branch" in errors
    assert "W9-P1: W9-T02 has empty owns" in errors


def test_excludes_remove_ownership_from_the_overlap_check(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - id: W9-P1
        mode: parallel
        after: []
        tasks:
          - {id: W9-T01, branch: feat/a, owns: [d/up/**], excludes: [d/up/x/**]}
          - {id: W9-T02, branch: feat/b, owns: [d/up/x/**]}
""",
    )
    assert validate_schedule(load_schedule(path)) == []


def test_two_globs_with_a_shared_prefix_overlap(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - id: W9-P1
        mode: parallel
        after: []
        tasks:
          - {id: W9-T01, branch: feat/a, owns: [d/**]}
          - {id: W9-T02, branch: feat/b, owns: [d/sub/**]}
""",
    )
    assert "W9-P1: W9-T01 and W9-T02 both own d/sub/**" in validate_schedule(load_schedule(path))


def test_a_glob_with_a_wildcard_in_the_middle_overlaps_a_literal_path(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - id: W9-P1
        mode: parallel
        after: []
        tasks:
          - {id: W9-T01, branch: feat/a, owns: ["deploy/upstream/**/values-gke.yaml"]}
          - {id: W9-T02, branch: feat/b, owns: [deploy/upstream/argo/values-gke.yaml]}
""",
    )
    assert validate_schedule(load_schedule(path)) == [
        "W9-P1: W9-T01 and W9-T02 both own deploy/upstream/argo/values-gke.yaml"
    ]


def test_probe_replaces_every_wildcard_with_x() -> None:
    assert swarm_lib._probe("deploy/upstream/**/values-gke.yaml") == "deploy/upstream/x/values-gke.yaml"
    assert swarm_lib._probe("a/b*.py") == "a/bx.py"
    assert swarm_lib._probe("a/?.py") == "a/x.py"
    assert swarm_lib._probe("a/[ab].py") == "a/x.py"
    assert swarm_lib._probe("a/b.py") == "a/b.py"


def test_deferred_to_must_be_a_later_sequential_stage_of_the_same_week(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - id: W9-P1
        mode: parallel
        after: []
        tasks:
          - {id: W9-T01, branch: feat/a, owns: [a/**], deferred_steps: [2], deferred_to: W9-P2}
          - {id: W9-T02, branch: feat/b, owns: [b/**], deferred_steps: [3], deferred_to: W9-S1}
      - id: W9-P2
        mode: parallel
        after: [W9-P1]
        tasks:
          - {id: W9-T03, branch: feat/c, owns: [c/**]}
      - {id: W9-S1, mode: sequential, after: [W9-P2], tasks: [{id: W9-T04, branch: feat/d}]}
""",
    )
    errors = validate_schedule(load_schedule(path))
    assert "W9-P1: W9-T01 deferred_to W9-P2 is not a later sequential stage of week 9" in errors
    assert not [e for e in errors if "W9-T02" in e]


def test_duplicate_task_ids_are_rejected(tmp_path: Path) -> None:
    path = write_schedule(
        tmp_path,
        """
  - week: 9
    stages:
      - id: W9-S1
        mode: sequential
        after: []
        tasks: [{id: W9-T01, branch: feat/a, combined_with: [W9-T02]}]
      - {id: W9-S2, mode: sequential, after: [W9-S1], tasks: [{id: W9-T02, branch: feat/b}]}
""",
    )
    assert "W9-S2: duplicate task W9-T02" in validate_schedule(load_schedule(path))


@pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6, 7, 8])
def test_wave_file_tables_match_the_yaml(week: int) -> None:
    """Verifies PG-16: each wave file's Execution schedule table is the table printed from the YAML."""
    errors = [e for e in swarm_lib.check_wave_tables(load_schedule()) if e.startswith(f"W{week}:")]
    assert errors == []


def test_validate_cli_reports_counts(capsys: pytest.CaptureFixture[str]) -> None:
    assert swarm_schedule.main(["validate"]) == 0
    assert capsys.readouterr().out.strip() == "schedule OK: 8 weeks, 39 stages, 94 tasks"


def test_table_cli_prints_the_wave_table(capsys: pytest.CaptureFixture[str]) -> None:
    assert swarm_schedule.main(["table", "--week", "1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(
        "| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |\n|---|---|---|---|---|\n"
    )
    assert (
        "| W1-P1 | parallel | W1-S2 | W1-T02 (`feat/w1-versions`); W1-T03+W1-T04 (`feat/w1-wiki`) "
        "| W1-T02 steps 8 → W1-S3 |" in out
    )


def test_next_and_done_follow_the_after_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    progress = tmp_path / "state" / "progress.json"
    monkeypatch.setattr(swarm_lib, "PROGRESS_PATH", progress)
    assert swarm_schedule.main(["next", "--week", "1"]) == 0
    assert capsys.readouterr().out.strip() == "W1-S1"
    assert swarm_schedule.main(["done", "W1-S1"]) == 0
    assert swarm_schedule.main(["done", "W1-S1"]) == 0  # idempotent
    assert swarm_lib.load_progress(progress) == {"done": ["W1-S1"], "stage_bases": {}}
    capsys.readouterr()
    assert swarm_schedule.main(["next", "--week", "1"]) == 0
    assert capsys.readouterr().out.strip() == "W1-S2"
    assert swarm_schedule.main(["next", "--week", "3"]) == 0
    assert capsys.readouterr().out.strip() == "W3-P1"


def test_done_rejects_an_unknown_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(swarm_lib, "PROGRESS_PATH", tmp_path / "progress.json")
    assert swarm_schedule.main(["done", "W9-S9"]) == 1
    assert not (tmp_path / "progress.json").exists()


def test_show_prints_owned_paths(capsys: pytest.CaptureFixture[str]) -> None:
    assert swarm_schedule.main(["show", "W1-P1"]) == 0
    out = capsys.readouterr().out
    assert "W1-T03+W1-T04 branch: feat/w1-wiki" in out
    assert "excludes: wiki/runbooks/local-up.md" in out
    assert "deferred_steps: 8 -> W1-S3" in out
