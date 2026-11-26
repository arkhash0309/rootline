"""Ownership check for parallel-stage task branches (PG-16, overview §7.4, gate check G1).

Usage:
  uv run python scripts/check_ownership.py --task <id> --base <sha> [--branch <ref>]
  uv run python scripts/check_ownership.py --stage <id> --base <sha> [--branch <ref>]

Exactly one of `--task` and `--stage` is required. `--task` is the check of a task branch of a parallel
stage. `--stage` is the check of an integration branch (gate check G1, ADR 0040 item 7): a changed path
passes when at least one task of the stage owns it (`owns` minus `excludes`), or it is always-allowed and
satisfies that path's special rule. A sequential stage has no `owns` lists and passes every path.

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

Exit codes: 0 every changed path passes; 1 at least one offending path (one stdout line per path,
`ownership: <path> not owned by <task id>` or `ownership: <path> not owned by any task of <stage id>`);
2 unknown task or stage, or a git failure (one stderr line).
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import sys
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run
from scripts.swarm_lib import (
    REPO,
    SCHEDULE_PATH,
    Schedule,
    Stage,
    TaskEntry,
    is_owned,
    load_schedule,
    matches,
)

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


def always_allowed_ok(
    repo: Path,
    path: str,
    merge_base: str,
    branch: str,
    read: Callable[[str, str], str | None] | None = None,
) -> bool:
    """Apply the special rule of an always-allowed path (module docstring); True when it holds.

    `read(ref, path)` returns the file content at `ref` or None; the default reads `repo` through git.
    """

    def reader(ref: str, file_path: str) -> str | None:
        return read(ref, file_path) if read is not None else read_at(repo, ref, file_path)

    name = path.rsplit("/", 1)[-1]
    if name == "__init__.py":
        content = reader(branch, path)
        return content is not None and is_marker_content(content)
    if name == "pyproject.toml":
        return pyproject_only_dependencies_changed(reader(merge_base, path), reader(branch, path))
    if path == "apps/console/package.json":
        return package_json_only_dependencies_changed(reader(merge_base, path), reader(branch, path))
    return True


def path_offenders(
    schedule: Schedule,
    owners: Sequence[TaskEntry],
    paths: Sequence[str],
    rule_ok: Callable[[str], bool],
    message: str,
) -> list[str]:
    """The single ownership rule used by `--task`, `--stage` and gate check G1 (ADR 0040 item 7).

    A path passes when it is owned (`owns` minus `excludes`) by at least one task of `owners`, or it matches
    `always_allowed` and `rule_ok(path)` (the special rule of that path) is True. `message` is the
    description after `not owned by ` in each returned line `ownership: <path> not owned by <message>`.
    """
    offenders = []
    for path in paths:
        if any(is_owned(task, path) for task in owners):
            continue
        if matches(path, schedule.always_allowed) and rule_ok(path):
            continue
        offenders.append(f"ownership: {path} not owned by {message}")
    return offenders


def stage_offenders(
    schedule: Schedule,
    stage: Stage,
    paths: Sequence[str],
    rule_ok: Callable[[str], bool],
) -> list[str]:
    """One `ownership: <path> not owned by any task of <stage>` line per offending path of `stage`."""
    if stage.mode != "parallel":
        return []
    return path_offenders(schedule, stage.tasks, paths, rule_ok, f"any task of {stage.id}")


def check_task(schedule: Schedule, task_id: str, base: str, branch: str, repo: Path = REPO) -> list[str]:
    """Return one `ownership: <path> not owned by <task>` line per offending path."""
    found = schedule.find_task(task_id)
    if found is None:
        raise KeyError(task_id)
    _, task = found
    if not task.owns:
        return []
    merge_base = git(repo, "merge-base", base, branch).strip()
    return path_offenders(
        schedule,
        [task],
        changed_files(repo, base, branch),
        lambda path: always_allowed_ok(repo, path, merge_base, branch),
        task_id,
    )


def check_stage(schedule: Schedule, stage_id: str, base: str, branch: str, repo: Path = REPO) -> list[str]:
    """Return one `ownership: <path> not owned by any task of <stage>` line per offending path."""
    stage = schedule.get_stage(stage_id)
    if stage is None:
        raise KeyError(stage_id)
    if stage.mode != "parallel":
        return []
    merge_base = git(repo, "merge-base", base, branch).strip()
    return stage_offenders(
        schedule,
        stage,
        changed_files(repo, base, branch),
        lambda path: always_allowed_ok(repo, path, merge_base, branch),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--task")
    selector.add_argument("--stage")
    parser.add_argument("--base", required=True)
    parser.add_argument("--branch", default="HEAD")
    args = parser.parse_args(argv)
    schedule = load_schedule(SCHEDULE_PATH)
    try:
        if args.task is not None:
            offenders = check_task(schedule, args.task, args.base, args.branch, REPO)
        else:
            offenders = check_stage(schedule, args.stage, args.base, args.branch, REPO)
    except KeyError:
        kind, ident = ("task", args.task) if args.task is not None else ("stage", args.stage)
        print(f"unknown {kind}: {ident}", file=sys.stderr)
        return 2
    except GitError as error:
        print(str(error), file=sys.stderr)
        return 2
    for line in offenders:
        print(line)
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
