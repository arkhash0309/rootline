"""Swarm schedule model, validation and progress state (PG-16, overview §7.2 and §7.4).

The committed schedule is `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`. Glob syntax in
`owns`, `excludes` and `always_allowed` is gitignore-style, relative to the repository root, evaluated
with `pathspec` (a pattern without a `/` is anchored at the repository root).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pathspec
import yaml

REPO = Path(__file__).resolve().parents[1]
SCHEDULE_PATH = REPO / "docs/superpowers/plans/2026-11-26-rootline-schedule.yaml"
PLANS_DIR = REPO / "docs/superpowers/plans"
PROGRESS_PATH = REPO / ".swarm/progress.json"

STAGE_ID_RE = re.compile(r"^W\d-[SP]\d$")
MIGRATIONS_PREFIX = "services/api/migrations/versions/"
GLOB_TOKEN_RE = re.compile(r"\*\*|\*|\?|\[[^\]]*\]")
TABLE_HEADER = "| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |"
TABLE_SEPARATOR = "|---|---|---|---|---|"


@dataclass
class TaskEntry:
    id: str
    branch: str | None = None
    combined_with: list[str] = field(default_factory=list)
    owns: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    pre_steps: list[int] = field(default_factory=list)
    deferred_steps: list[int] = field(default_factory=list)
    deferred_to: str | None = None


@dataclass
class Stage:
    id: str
    mode: str
    after: list[str] = field(default_factory=list)
    tasks: list[TaskEntry] = field(default_factory=list)
    uses_cluster: bool = False


@dataclass
class Week:
    week: int
    stages: list[Stage] = field(default_factory=list)


@dataclass
class Schedule:
    version: int
    max_parallel_implementers: int
    always_allowed: list[str] = field(default_factory=list)
    weeks: list[Week] = field(default_factory=list)

    def all_stages(self) -> list[Stage]:
        """Every stage in execution order (file order)."""
        return [stage for week in self.weeks for stage in week.stages]

    def get_stage(self, stage_id: str) -> Stage | None:
        for stage in self.all_stages():
            if stage.id == stage_id:
                return stage
        return None

    def get_week(self, number: int) -> Week | None:
        for week in self.weeks:
            if week.week == number:
                return week
        return None

    def find_task(self, task_id: str) -> tuple[Stage, TaskEntry] | None:
        """Find a task by its own ID or by an ID listed in a task's `combined_with`."""
        for stage in self.all_stages():
            for task in stage.tasks:
                if task.id == task_id or task_id in task.combined_with:
                    return stage, task
        return None


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if value else []


def _int_list(value: Any) -> list[int]:
    return [int(item) for item in value] if value else []


def load_schedule(path: Path = SCHEDULE_PATH) -> Schedule:
    """Parse the schedule YAML. Raises ValueError when the file is not a mapping with `weeks`."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict) or not isinstance(raw.get("weeks"), list):
        raise ValueError(f"{path}: schedule must be a mapping with a `weeks` list")
    weeks: list[Week] = []
    for raw_week in raw["weeks"]:
        stages: list[Stage] = []
        for raw_stage in raw_week.get("stages") or []:
            tasks = [
                TaskEntry(
                    id=str(raw_task["id"]),
                    branch=raw_task.get("branch"),
                    combined_with=_str_list(raw_task.get("combined_with")),
                    owns=_str_list(raw_task.get("owns")),
                    excludes=_str_list(raw_task.get("excludes")),
                    pre_steps=_int_list(raw_task.get("pre_steps")),
                    deferred_steps=_int_list(raw_task.get("deferred_steps")),
                    deferred_to=raw_task.get("deferred_to"),
                )
                for raw_task in raw_stage.get("tasks") or []
            ]
            stages.append(
                Stage(
                    id=str(raw_stage["id"]),
                    mode=str(raw_stage.get("mode", "")),
                    after=_str_list(raw_stage.get("after")),
                    tasks=tasks,
                    uses_cluster=bool(raw_stage.get("uses_cluster", False)),
                )
            )
        weeks.append(Week(week=int(raw_week["week"]), stages=stages))
    return Schedule(
        version=int(raw.get("version", 1)),
        max_parallel_implementers=int(raw.get("max_parallel_implementers", 3)),
        always_allowed=_str_list(raw.get("always_allowed")),
        weeks=weeks,
    )


@lru_cache(maxsize=512)
def _spec(globs: tuple[str, ...]) -> pathspec.GitIgnoreSpec:
    return pathspec.GitIgnoreSpec.from_lines(glob if "/" in glob else "/" + glob for glob in globs)


def matches(path: str, globs: list[str]) -> bool:
    """True when `path` (repository-relative, `/` separators) matches any gitignore-style glob."""
    if not globs:
        return False
    return _spec(tuple(globs)).match_file(path)


def is_owned(task: TaskEntry, path: str) -> bool:
    """`owns` minus `excludes` (overview §7.4)."""
    return matches(path, task.owns) and not matches(path, task.excludes)


def _probe(glob: str) -> str:
    """A concrete path that `glob` matches: every `**`, `*`, `?` and `[...]` is replaced with `x`.

    `deploy/upstream/**/values-gke.yaml` becomes `deploy/upstream/x/values-gke.yaml`; a literal path is
    returned unchanged.
    """
    return GLOB_TOKEN_RE.sub("x", glob)


def _representatives(task: TaskEntry) -> list[tuple[str, str]]:
    """(label, probe path) pairs: one per owned glob, the probe being `_probe(glob)`."""
    return [(glob, _probe(glob)) for glob in task.owns]


def _adds_alembic_revision(task: TaskEntry) -> bool:
    return any(glob.startswith(MIGRATIONS_PREFIX) for glob in task.owns)


def validate_schedule(schedule: Schedule) -> list[str]:
    """Check the rules of overview §7.2 and return one error string per violation (empty = valid)."""
    errors: list[str] = []
    stages = schedule.all_stages()
    seen_stage_ids: list[str] = []
    seen_task_ids: set[str] = set()
    stage_week: dict[str, int] = {}
    for week in schedule.weeks:
        for stage in week.stages:
            stage_week[stage.id] = week.week
    for index, stage in enumerate(stages):
        if stage.id in seen_stage_ids:
            errors.append(f"{stage.id}: duplicate stage id")
        elif not STAGE_ID_RE.fullmatch(stage.id):
            errors.append(f"{stage.id}: stage id does not match {STAGE_ID_RE.pattern}")
        if stage.mode not in ("sequential", "parallel"):
            errors.append(f"{stage.id}: invalid mode {stage.mode!r}")
        earlier = {s.id for s in stages[:index]}
        for dependency in stage.after:
            if dependency in earlier:
                continue
            if dependency in stage_week:
                errors.append(f"{stage.id}: stage in after is not earlier: {dependency}")
            else:
                errors.append(f"{stage.id}: unknown stage in after: {dependency}")
        for task in stage.tasks:
            for task_id in (task.id, *task.combined_with):
                if task_id in seen_task_ids:
                    errors.append(f"{stage.id}: duplicate task {task_id}")
                seen_task_ids.add(task_id)
            if task.deferred_steps:
                errors.extend(_deferred_errors(schedule, stage, task))
        if stage.mode == "parallel":
            errors.extend(_parallel_errors(schedule, stage))
        seen_stage_ids.append(stage.id)
    return errors


def _deferred_errors(schedule: Schedule, stage: Stage, task: TaskEntry) -> list[str]:
    if not task.deferred_to:
        return [f"{stage.id}: {task.id} has deferred_steps but no deferred_to"]
    week_number = next((w.week for w in schedule.weeks if stage in w.stages), None)
    week = schedule.get_week(week_number) if week_number is not None else None
    target = None
    later = False
    if week is not None:
        position = week.stages.index(stage)
        for offset, candidate in enumerate(week.stages):
            if candidate.id == task.deferred_to:
                target = candidate
                later = offset > position
    if target is None or target.mode != "sequential" or not later:
        return [
            f"{stage.id}: {task.id} deferred_to {task.deferred_to} "
            f"is not a later sequential stage of week {week_number}"
        ]
    return []


def _parallel_errors(schedule: Schedule, stage: Stage) -> list[str]:
    errors: list[str] = []
    if stage.uses_cluster:
        errors.append(f"{stage.id}: parallel stage must not use the cluster")
    for task in stage.tasks:
        if not task.branch:
            errors.append(f"{stage.id}: {task.id} has no branch")
        if not task.owns:
            errors.append(f"{stage.id}: {task.id} has empty owns")
    reported: set[tuple[str, str, str]] = set()
    for i, first in enumerate(stage.tasks):
        for second in stage.tasks[i + 1 :]:
            for owner, other in ((first, second), (second, first)):
                for label, probe in _representatives(owner):
                    if matches(probe, schedule.always_allowed):
                        continue
                    if not is_owned(owner, probe) or not is_owned(other, probe):
                        continue
                    key = (first.id, second.id, label)
                    if key in reported:
                        continue
                    reported.add(key)
                    errors.append(f"{stage.id}: {first.id} and {second.id} both own {label}")
    if sum(1 for task in stage.tasks if _adds_alembic_revision(task)) > 1:
        errors.append(f"{stage.id}: two tasks add Alembic revisions")
    return errors


def render_table(week: Week) -> str:
    """The Markdown "Execution schedule" table of a wave file (overview §7.2)."""
    lines = [TABLE_HEADER, TABLE_SEPARATOR]
    for stage in week.stages:
        after = ", ".join(stage.after) if stage.after else "—"
        task_cells = []
        for task in stage.tasks:
            label = "+".join([task.id, *task.combined_with])
            branch = f"`{task.branch}`" if task.branch else "no branch"
            task_cells.append(f"{label} ({branch})")
        deferred_cells = [
            f"{task.id} steps {', '.join(str(n) for n in task.deferred_steps)} → {task.deferred_to}"
            for task in stage.tasks
            if task.deferred_steps
        ]
        deferred_cells += [
            f"{task.id} pre-dispatch steps {', '.join(str(n) for n in task.pre_steps)} (coordinator)"
            for task in stage.tasks
            if task.pre_steps
        ]
        deferred = "; ".join(deferred_cells) if deferred_cells else "—"
        lines.append(f"| {stage.id} | {stage.mode} | {after} | {'; '.join(task_cells)} | {deferred} |")
    return "\n".join(lines)


def _extract_table(text: str) -> str | None:
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.startswith("| Stage |"):
            end = start
            while end < len(lines) and lines[end].startswith("|"):
                end += 1
            return "\n".join(lines[start:end])
    return None


def check_wave_tables(schedule: Schedule, plans_dir: Path = PLANS_DIR) -> list[str]:
    """Compare each wave file's "Execution schedule" table with the table rendered from the YAML."""
    errors: list[str] = []
    for week in schedule.weeks:
        files = sorted(plans_dir.glob(f"*-w{week.week}-*.md"))
        if len(files) != 1:
            errors.append(f"W{week.week}: expected exactly one wave file matching *-w{week.week}-*.md")
            continue
        table = _extract_table(files[0].read_text(encoding="utf-8"))
        if table is None:
            errors.append(f"W{week.week}: {files[0].name} has no execution schedule table")
        elif table != render_table(week):
            errors.append(
                f"W{week.week}: execution schedule table in {files[0].name} differs from the YAML "
                f"(print it with: uv run python scripts/swarm_schedule.py table --week {week.week})"
            )
    return errors


def load_progress(path: Path = PROGRESS_PATH) -> dict[str, Any]:
    """Read `.swarm/progress.json`; a missing file is `{"done": [], "stage_bases": {}}`."""
    if not path.exists():
        return {"done": [], "stage_bases": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"done": list(data.get("done", [])), "stage_bases": dict(data.get("stage_bases", {}))}


def save_progress(progress: dict[str, Any], path: Path = PROGRESS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def next_stage(schedule: Schedule, week_number: int, done: list[str]) -> Stage | None:
    """First stage of the week that is not done and whose `after` stages are all done."""
    week = schedule.get_week(week_number)
    if week is None:
        return None
    for stage in week.stages:
        if stage.id not in done and all(dep in done for dep in stage.after):
            return stage
    return None
