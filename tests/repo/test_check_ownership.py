"""Verifies PG-16 (overview §7.4 ownership rules, gate check G1)."""

from pathlib import Path

import pytest

from scripts import check_ownership
from scripts.proc import run
from scripts.swarm_lib import load_schedule

SCHEDULE = """
version: 1
max_parallel_implementers: 3
always_allowed:
  - wiki/log.md
  - uv.lock
  - "**/__init__.py"
  - "**/pyproject.toml"
  - apps/console/package.json
weeks:
  - week: 9
    stages:
      - id: W9-S1
        mode: sequential
        after: []
        tasks: [{id: W9-T09, branch: feat/seq}]
      - id: W9-P1
        mode: parallel
        after: [W9-S1]
        tasks:
          - id: W9-T01
            branch: feat/a
            combined_with: [W9-T02]
            owns: ["svc/a/**"]
            excludes: ["svc/a/locked/**"]
          - {id: W9-T03, branch: feat/b, owns: ["svc/b/**"]}
"""

OTHER_PYPROJECT = """[project]
name = "other"
version = "0.1.0"
dependencies = ["a"]

[dependency-groups]
dev = ["pytest"]
"""

PACKAGE_JSON = '{"name": "console", "version": "1.0.0", "dependencies": {"next": "16.0.0"}}\n'


def git(repo: Path, *args: str) -> str:
    result = run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ]
    )
    return result.stdout.strip()


def write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "develop")
    write(root, "svc/a/x.py", "x = 1\n")
    write(root, "svc/a/locked/y.py", "y = 1\n")
    write(root, "libs/other/pyproject.toml", OTHER_PYPROJECT)
    write(root, "apps/console/package.json", PACKAGE_JSON)
    write(root, "wiki/log.md", "# Log\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root, git(root, "rev-parse", "HEAD")


def commit_change(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        write(root, rel, content)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")


def offenders(tmp_path: Path, root: Path, base: str, task: str = "W9-T01") -> list[str]:
    schedule_file = tmp_path / "schedule.yaml"
    schedule_file.write_text(SCHEDULE, encoding="utf-8")
    return check_ownership.check_task(load_schedule(schedule_file), task, base, "HEAD", root)


def test_change_inside_owns_passes(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(root, {"svc/a/x.py": "x = 2\n", "svc/a/new/z.py": "z = 1\n"})
    assert offenders(tmp_path, root, base) == []


def test_change_in_excludes_fails(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(root, {"svc/a/locked/y.py": "y = 2\n"})
    assert offenders(tmp_path, root, base) == ["ownership: svc/a/locked/y.py not owned by W9-T01"]


def test_change_outside_owns_fails(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(root, {"svc/b/q.py": "q = 1\n", "svc/a/x.py": "x = 3\n"})
    assert offenders(tmp_path, root, base) == ["ownership: svc/b/q.py not owned by W9-T01"]


def test_always_allowed_paths_pass(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(root, {"wiki/log.md": "# Log\n- [agent] x\n", "uv.lock": "version = 1\n"})
    assert offenders(tmp_path, root, base) == []


def test_non_empty_init_outside_owns_fails_and_empty_one_passes(
    tmp_path: Path, repo: tuple[Path, str]
) -> None:
    root, base = repo
    commit_change(root, {"libs/other/pkg/__init__.py": "import os\n", "libs/other/empty/__init__.py": ""})
    assert offenders(tmp_path, root, base) == ["ownership: libs/other/pkg/__init__.py not owned by W9-T01"]


def test_docstring_only_init_passes(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(root, {"libs/other/doc/__init__.py": '"""Package marker."""\n'})
    assert offenders(tmp_path, root, base) == []


def test_deleted_init_outside_owns_fails(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, _ = repo
    commit_change(root, {"libs/other/gone/__init__.py": ""})
    base_with_init = git(root, "rev-parse", "HEAD")
    git(root, "rm", "-q", "libs/other/gone/__init__.py")
    git(root, "commit", "-q", "-m", "delete")
    assert offenders(tmp_path, root, base_with_init) == [
        "ownership: libs/other/gone/__init__.py not owned by W9-T01"
    ]


def test_pyproject_dependency_change_passes(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(
        root,
        {
            "libs/other/pyproject.toml": OTHER_PYPROJECT.replace('["a"]', '["a", "b"]').replace(
                '["pytest"]', '["pytest", "x"]'
            )
        },
    )
    assert offenders(tmp_path, root, base) == []


def test_pyproject_name_change_fails(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(
        root, {"libs/other/pyproject.toml": OTHER_PYPROJECT.replace('name = "other"', 'name = "renamed"')}
    )
    assert offenders(tmp_path, root, base) == ["ownership: libs/other/pyproject.toml not owned by W9-T01"]


def test_package_json_dependency_change_passes_and_name_change_fails(
    tmp_path: Path, repo: tuple[Path, str]
) -> None:
    root, base = repo
    commit_change(root, {"apps/console/package.json": PACKAGE_JSON.replace('"16.0.0"', '"16.1.0"')})
    assert offenders(tmp_path, root, base) == []
    commit_change(root, {"apps/console/package.json": PACKAGE_JSON.replace('"console"', '"renamed"')})
    assert offenders(tmp_path, root, base) == ["ownership: apps/console/package.json not owned by W9-T01"]


def test_sequential_task_always_passes(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(
        root, {"anything/at/all.txt": "x\n", "libs/other/pyproject.toml": "[project]\nname = 'z'\n"}
    )
    assert offenders(tmp_path, root, base, task="W9-T09") == []


def test_combined_task_uses_the_owns_of_its_branch_entry(tmp_path: Path, repo: tuple[Path, str]) -> None:
    root, base = repo
    commit_change(root, {"svc/a/x.py": "x = 5\n", "svc/b/q.py": "q = 1\n"})
    assert offenders(tmp_path, root, base, task="W9-T02") == ["ownership: svc/b/q.py not owned by W9-T02"]


def test_unknown_task_is_an_error_exit(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_ownership.main(["--task", "W0-T99", "--base", "HEAD", "--branch", "HEAD"]) == 2
    assert "unknown task: W0-T99" in capsys.readouterr().err


def test_cli_exit_codes(
    tmp_path: Path,
    repo: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base = repo
    schedule_file = tmp_path / "schedule.yaml"
    schedule_file.write_text(SCHEDULE, encoding="utf-8")
    monkeypatch.setattr(check_ownership, "SCHEDULE_PATH", schedule_file)
    monkeypatch.setattr(check_ownership, "REPO", root)
    commit_change(root, {"svc/b/q.py": "q = 1\n"})
    assert check_ownership.main(["--task", "W9-T01", "--base", base]) == 1
    assert capsys.readouterr().out.strip() == "ownership: svc/b/q.py not owned by W9-T01"
    assert check_ownership.main(["--task", "W9-T03", "--base", base, "--branch", "HEAD"]) == 0
