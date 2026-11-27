"""Verifies CI-001, WIK-020 and PG-21 for scripts/ci_changed_files.py (PG-26, ADR 0045 D1, D2).

The script lists the files changed between two revisions for the `wiki` job of `ci.yml` (WIK-020). The
change-set rule is the PG-21 rule of `scripts/check_ownership.py`: `--diff-filter=ACMRD --no-renames`, so a
rename is a deletion plus an addition. Every test builds a throw-away repository under `tmp_path` and makes
no network call.
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import ci_changed_files
from scripts.proc import run


def git(repo: Path, *args: str) -> str:
    result = run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            *args,
        ]
    )
    return result.stdout.strip()


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def init_repo(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repository with branch `feat` that adds z.txt and a.txt, modifies b.txt and deletes c.txt."""
    root = init_repo(tmp_path / "repo")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    (root / "c.txt").write_text("c\n", encoding="utf-8")
    commit_all(root, "base")
    git(root, "switch", "-q", "-c", "feat")
    (root / "z.txt").write_text("z\n", encoding="utf-8")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "b.txt").write_text("b changed\n", encoding="utf-8")
    (root / "c.txt").unlink()
    commit_all(root, "change")
    return root


def test_lists_added_modified_deleted_sorted(repo: Path) -> None:
    """Verifies CI-001, PG-21: added, modified and deleted paths, sorted by code point."""
    assert ci_changed_files.changed_files("main", "HEAD", repo) == ["a.txt", "b.txt", "c.txt", "z.txt"]


def test_rename_lists_old_and_new_path(tmp_path: Path) -> None:
    """Verifies PG-21: a rename is the deleted old path plus the added new path."""
    root = init_repo(tmp_path / "repo")
    (root / "old.txt").write_text(
        "content that is long enough to be detected as a rename\n", encoding="utf-8"
    )
    commit_all(root, "base")
    git(root, "switch", "-q", "-c", "feat")
    git(root, "mv", "old.txt", "new.txt")
    commit_all(root, "rename")
    assert ci_changed_files.changed_files("main", "HEAD", root) == ["new.txt", "old.txt"]


def test_three_dot_ignores_later_base_commits(tmp_path: Path) -> None:
    """Verifies CI-001: `<base>...<head>` uses the merge base, so later base commits are not listed."""
    root = init_repo(tmp_path / "repo")
    (root / "keep.txt").write_text("keep\n", encoding="utf-8")
    commit_all(root, "base")
    git(root, "switch", "-q", "-c", "feat")
    (root / "mine.txt").write_text("mine\n", encoding="utf-8")
    commit_all(root, "mine")
    git(root, "switch", "-q", "main")
    (root / "late.txt").write_text("late\n", encoding="utf-8")
    commit_all(root, "late on main")
    git(root, "switch", "-q", "feat")
    assert ci_changed_files.changed_files("main", "HEAD", root) == ["mine.txt"]


def test_empty_change_set(tmp_path: Path) -> None:
    """Verifies CI-001, WIK-020: an empty change set writes an empty file and exits 0."""
    root = init_repo(tmp_path / "repo")
    (root / "only.txt").write_text("only\n", encoding="utf-8")
    commit_all(root, "base")
    out = tmp_path / "out.txt"
    code = ci_changed_files.main(
        ["--base", "main", "--head", "main", "--repo", str(root), "--output", str(out)]
    )
    assert code == 0
    assert out.read_text(encoding="utf-8") == ""


def test_output_file_format(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies CI-001, WIK-020: one path per line, LF endings, nothing on stdout with `--output`."""
    out = tmp_path / "out.txt"
    code = ci_changed_files.main(
        ["--base", "main", "--head", "HEAD", "--repo", str(repo), "--output", str(out)]
    )
    assert code == 0
    assert out.read_bytes() == b"a.txt\nb.txt\nc.txt\nz.txt\n"
    assert capsys.readouterr().out == ""


def test_stdout_without_output(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies CI-001: without `--output` the text goes to stdout."""
    code = ci_changed_files.main(["--base", "main", "--head", "HEAD", "--repo", str(repo)])
    assert code == 0
    assert capsys.readouterr().out == "a.txt\nb.txt\nc.txt\nz.txt\n"


def test_unknown_ref_exits_2(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies CI-001: an unknown revision gives exit 2 and one `git failed` stderr line."""
    code = ci_changed_files.main(["--base", "nope", "--head", "HEAD", "--repo", str(repo)])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert len(captured.err.splitlines()) == 1
    assert captured.err.startswith("ci_changed_files: git failed: ")


def test_repo_not_found_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies CI-001: a missing `--repo` directory gives exit 2 without starting git."""
    missing = tmp_path / "missing"
    code = ci_changed_files.main(["--base", "main", "--head", "HEAD", "--repo", str(missing)])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert captured.err == f"ci_changed_files: repo not found: {missing}\n"


def test_output_not_writable_exits_2(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifies CI-001, WIK-020: an unwritable `--output` path gives exit 2 and one stderr line."""
    target = tmp_path / "no-dir" / "out.txt"
    code = ci_changed_files.main(
        ["--base", "main", "--head", "HEAD", "--repo", str(repo), "--output", str(target)]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err == f"ci_changed_files: output not writable: {target}\n"


def test_git_missing_exits_2(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies CI-001: a missing `git` executable gives exit 2 and `git missing`."""

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("git")

    monkeypatch.setattr(ci_changed_files, "run", fake_run)
    code = ci_changed_files.main(["--base", "main", "--head", "HEAD", "--repo", str(repo)])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err == "ci_changed_files: git missing\n"


def test_timeout_exits_2(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies CI-001: a `git` call that exceeds 120 s gives exit 2 and `timeout`."""

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd=["git"], timeout=120)

    monkeypatch.setattr(ci_changed_files, "run", fake_run)
    code = ci_changed_files.main(["--base", "main", "--head", "HEAD", "--repo", str(repo)])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err == "ci_changed_files: timeout\n"
