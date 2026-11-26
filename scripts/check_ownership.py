"""Ownership check for parallel-stage task branches (PG-16, overview §7.4, gate check G1).

Usage:
  uv run python scripts/check_ownership.py --task <id> --base <sha> [--branch <ref>]

Changed files are `git diff --name-only --diff-filter=ACMRD --no-renames -z <base>...<branch>`
(`--branch` defaults to `HEAD`). A task without `owns` (a task of a sequential stage) passes for every
path. Otherwise a changed path passes when it matches `owns` minus `excludes`, or matches
`always_allowed` and satisfies that path's special rule:

Special rules per always-allowed pattern:

- `**/__init__.py`: the file exists on the branch and is empty or holds a single docstring line.
- `**/pyproject.toml`: the file exists on both sides and differs only in `project.dependencies`,
  `project.optional-dependencies` and `dependency-groups`.
- `apps/console/package.json`: the file exists on both sides and differs only in `dependencies`,
  `devDependencies`, `peerDependencies` and `optionalDependencies`.
- Every other always-allowed path: no rule.

Exit codes: 0 every changed path is owned; 1 at least one offending path (one line per path,
`ownership: <path> not owned by <task>`); 2 unknown task or a git failure.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run
from scripts.swarm_lib import REPO, SCHEDULE_PATH, Schedule, is_owned, load_schedule, matches

PYPROJECT_DEPENDENCY_KEYS = (("project", "dependencies"), ("project", "optional-dependencies"))
PYPROJECT_DEPENDENCY_TABLES = ("dependency-groups",)
PACKAGE_JSON_DEPENDENCY_KEYS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


class GitError(RuntimeError):
    """A git command exited non-zero."""


def git(repo: Path, *args: str) -> str:
    result = run(["git", "-C", str(repo), *args], check=False)
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def changed_files(repo: Path, base: str, branch: str) -> list[str]:
    out = git(repo, "diff", "--name-only", "--diff-filter=ACMRD", "--no-renames", "-z", f"{base}...{branch}")
    return [path for path in out.split("\0") if path]


def read_at(repo: Path, ref: str, path: str) -> str | None:
    """File content at `ref`, or None when the path does not exist there."""
    result = run(["git", "-C", str(repo), "show", f"{ref}:{path}"], check=False)
    return result.stdout if result.returncode == 0 else None


def is_marker_content(text: str) -> bool:
    """True for an empty file or a file whose only statement is one docstring line."""
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped.splitlines()) != 1:
        return False
    try:
        tree = ast.parse(stripped)
    except SyntaxError:
        return False
    return (
        len(tree.body) == 1
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    )


def _without_pyproject_dependencies(data: dict[str, Any]) -> dict[str, Any]:
    stripped = copy.deepcopy(data)
    for table, key in PYPROJECT_DEPENDENCY_KEYS:
        stripped.get(table, {}).pop(key, None)
    for table in PYPROJECT_DEPENDENCY_TABLES:
        stripped.pop(table, None)
    return stripped


def pyproject_only_dependencies_changed(old: str | None, new: str | None) -> bool:
    if old is None or new is None:
        return False
    try:
        return _without_pyproject_dependencies(tomllib.loads(old)) == _without_pyproject_dependencies(
            tomllib.loads(new)
        )
    except tomllib.TOMLDecodeError:
        return False


def package_json_only_dependencies_changed(old: str | None, new: str | None) -> bool:
    if old is None or new is None:
        return False
    try:
        old_data, new_data = json.loads(old), json.loads(new)
    except json.JSONDecodeError:
        return False
    for key in PACKAGE_JSON_DEPENDENCY_KEYS:
        old_data.pop(key, None)
        new_data.pop(key, None)
    return bool(old_data == new_data)


def always_allowed_ok(repo: Path, path: str, merge_base: str, branch: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if name == "__init__.py":
        content = read_at(repo, branch, path)
        return content is not None and is_marker_content(content)
    if name == "pyproject.toml":
        return pyproject_only_dependencies_changed(
            read_at(repo, merge_base, path), read_at(repo, branch, path)
        )
    if path == "apps/console/package.json":
        return package_json_only_dependencies_changed(
            read_at(repo, merge_base, path), read_at(repo, branch, path)
        )
    return True


def check_task(schedule: Schedule, task_id: str, base: str, branch: str, repo: Path = REPO) -> list[str]:
    """Return one `ownership: <path> not owned by <task>` line per offending path."""
    found = schedule.find_task(task_id)
    if found is None:
        raise KeyError(task_id)
    _, task = found
    if not task.owns:
        return []
    merge_base = git(repo, "merge-base", base, branch).strip()
    offenders = []
    for path in changed_files(repo, base, branch):
        if is_owned(task, path):
            continue
        if matches(path, schedule.always_allowed) and always_allowed_ok(repo, path, merge_base, branch):
            continue
        offenders.append(f"ownership: {path} not owned by {task_id}")
    return offenders


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--task", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--branch", default="HEAD")
    args = parser.parse_args(argv)
    try:
        offenders = check_task(load_schedule(SCHEDULE_PATH), args.task, args.base, args.branch, REPO)
    except KeyError:
        print(f"unknown task: {args.task}", file=sys.stderr)
        return 2
    except GitError as error:
        print(str(error), file=sys.stderr)
        return 2
    for line in offenders:
        print(line)
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
