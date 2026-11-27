"""List the files a pull request changes, for the `wiki` job of `ci.yml` (CI-001, WIK-020).

Usage:
  uv run python scripts/ci_changed_files.py --base <ref> --head <ref> [--output <file>] [--repo <dir>]

The changed files are `git diff --name-only --diff-filter=ACMRD --no-renames -z <base>...<head>`: the
three-dot form compares `<head>` with the merge base of `<base>` and `<head>`, so commits that landed on
`<base>` after the branch point are not listed. A rename is a deletion of the old path plus an addition
of the new path, and both paths are listed (the same rule as `scripts/check_ownership.py`, PG-21).

Output: one path per line, sorted, each line ending in `\\n`; an empty change set writes an empty file or
no stdout. `--output` writes the file (UTF-8) instead of stdout. `--repo` is the repository directory
(default: the repository that contains this script). `wiki_lint.py --changed-files` reads this output.

Exit codes: 0 success; 2 `git` failed (unknown ref, not a repository): one stderr line
`ci_changed_files: git failed: <first line of git stderr>`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]


class GitError(Exception):
    """`git diff` exited non-zero; the message is the first line of its stderr."""


def changed_files(base: str, head: str, repo: Path = REPO) -> list[str]:
    """Return the sorted paths changed between `base...head` in `repo` (CI-001)."""
    cmd = [
        "git",
        "-C",
        str(repo),
        "diff",
        "--name-only",
        "--diff-filter=ACMRD",
        "--no-renames",
        "-z",
        f"{base}...{head}",
    ]
    try:
        proc = run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        lines = exc.stderr.strip().splitlines() if exc.stderr else []
        raise GitError(lines[0] if lines else f"exit {exc.returncode}") from exc
    return sorted(p for p in proc.stdout.split("\0") if p)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List files changed between two refs (CI-001).")
    ap.add_argument("--base", required=True, help="base ref, for example origin/develop")
    ap.add_argument("--head", required=True, help="head ref, for example HEAD")
    ap.add_argument("--output", help="file to write instead of stdout")
    ap.add_argument("--repo", default=str(REPO), help="repository directory")
    args = ap.parse_args(argv)
    try:
        paths = changed_files(args.base, args.head, Path(args.repo))
    except GitError as exc:
        print(f"ci_changed_files: git failed: {exc}", file=sys.stderr)
        return 2
    text = "".join(f"{p}\n" for p in paths)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
