"""List the files a pull request changes, for the `wiki` job of `ci.yml` (CI-001, WIK-020, PG-21, PG-26).

Usage:
  uv run python scripts/ci_changed_files.py --base <ref> --head <ref> [--output <file>] [--repo <dir>]

The changed files are `git diff --name-only --diff-filter=ACMRD --no-renames -z <base>...<head>`: the
three-dot form compares `<head>` with the merge base of `<base>` and `<head>`, so commits that reached
`<base>` after the branch point are not listed. A rename is listed as the deleted old path plus the added
new path (PG-21, the rule of `scripts/check_ownership.py`).

Output: the paths sorted with `sorted()`, one per line, each line ending in LF; an empty change set gives
the empty string. `--output` writes the text to that file (UTF-8) and prints nothing to stdout; without
`--output` the text goes to stdout. `--repo` is the repository directory (default: the repository that
contains this script). Callers MUST pass refs that do not start with `-`; `git` validates ref syntax.
`scripts/wiki_lint.py --changed-files` reads this output.

Exit codes: 0 success; 2 every handled failure, with exactly one stderr line `ci_changed_files: <reason>`
(`repo not found: <dir>`, `git missing`, `timeout`, `git failed: <msg>`, `output not writable: <path>`),
or argparse's usage error. Any other exception is a defect and ends with a traceback and exit 1
(ADR 0045 D2).
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
GIT_TIMEOUT_SECONDS = 120


class ChangedFilesError(Exception):
    """A handled failure; `str(exc)` is the reason without the `ci_changed_files: ` prefix."""


def changed_files(
    base: str, head: str, repo: Path = REPO, *, timeout: int = GIT_TIMEOUT_SECONDS
) -> list[str]:
    """Return the sorted paths changed between `base...head` in `repo` (CI-001, PG-21)."""
    if not Path(repo).is_dir():
        raise ChangedFilesError(f"repo not found: {repo}")
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
        proc = run(cmd, check=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise ChangedFilesError("git missing") from exc
    except subprocess.TimeoutExpired as exc:
        raise ChangedFilesError("timeout") from exc
    except subprocess.CalledProcessError as exc:
        stderr_lines = (exc.stderr or "").strip().splitlines()
        message = stderr_lines[0] if stderr_lines else f"exit {exc.returncode}"
        raise ChangedFilesError(f"git failed: {message}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ChangedFilesError(f"git failed: {exc}") from exc
    return sorted(path for path in proc.stdout.split("\0") if path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List files changed between two revisions (CI-001, WIK-020).")
    ap.add_argument("--base", required=True, help="base revision, for example origin/develop")
    ap.add_argument("--head", required=True, help="head revision, for example HEAD")
    ap.add_argument("--output", help="file to write (UTF-8) instead of stdout")
    ap.add_argument("--repo", default=str(REPO), help="repository directory passed to `git -C`")
    args = ap.parse_args(argv)
    try:
        paths = changed_files(args.base, args.head, Path(args.repo))
    except ChangedFilesError as exc:
        print(f"ci_changed_files: {exc}", file=sys.stderr)
        return 2
    text = "".join(f"{path}\n" for path in paths)
    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError:
            print(f"ci_changed_files: output not writable: {args.output}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
