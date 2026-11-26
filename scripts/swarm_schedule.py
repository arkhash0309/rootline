"""Swarm schedule CLI (PG-16, overview §7.9).

Usage:
  uv run python scripts/swarm_schedule.py validate
  uv run python scripts/swarm_schedule.py next --week N
  uv run python scripts/swarm_schedule.py done <stage>
  uv run python scripts/swarm_schedule.py show <stage>
  uv run python scripts/swarm_schedule.py table --week N

Exit codes: 0 success; 1 validation errors, unknown stage or week, or no runnable stage.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import swarm_lib


def cmd_validate() -> int:
    schedule = swarm_lib.load_schedule()
    errors = swarm_lib.validate_schedule(schedule) + swarm_lib.check_wave_tables(schedule)
    if errors:
        for error in errors:
            print(error)
        return 1
    stages = schedule.all_stages()
    tasks = sum(1 + len(task.combined_with) for stage in stages for task in stage.tasks)
    print(f"schedule OK: {len(schedule.weeks)} weeks, {len(stages)} stages, {tasks} tasks")
    return 0


def cmd_next(week: int) -> int:
    schedule = swarm_lib.load_schedule()
    week_entry = schedule.get_week(week)
    if week_entry is None:
        print(f"unknown week: {week}")
        return 1
    done = swarm_lib.load_progress(swarm_lib.PROGRESS_PATH)["done"]
    stage = swarm_lib.next_stage(schedule, week, done)
    if stage is not None:
        print(stage.id)
        return 0
    if all(s.id in done for s in week_entry.stages):
        print(f"week {week} complete")
        return 0
    waiting = [s.id for s in week_entry.stages if s.id not in done]
    print(f"no runnable stage in week {week}; not done: {', '.join(waiting)}")
    return 1


def cmd_done(stage_id: str) -> int:
    schedule = swarm_lib.load_schedule()
    if schedule.get_stage(stage_id) is None:
        print(f"unknown stage: {stage_id}")
        return 1
    progress = swarm_lib.load_progress(swarm_lib.PROGRESS_PATH)
    if stage_id not in progress["done"]:
        progress["done"].append(stage_id)
        swarm_lib.save_progress(progress, swarm_lib.PROGRESS_PATH)
    print(f"done: {stage_id}")
    return 0


def cmd_show(stage_id: str) -> int:
    schedule = swarm_lib.load_schedule()
    stage = schedule.get_stage(stage_id)
    if stage is None:
        print(f"unknown stage: {stage_id}")
        return 1
    print(f"{stage.id} ({stage.mode}) after: {', '.join(stage.after) if stage.after else '-'}")
    for task in stage.tasks:
        label = "+".join([task.id, *task.combined_with])
        print(f"- {label} branch: {task.branch or 'none'}")
        print(f"  owns: {', '.join(task.owns) if task.owns else '-'}")
        print(f"  excludes: {', '.join(task.excludes) if task.excludes else '-'}")
        print(f"  pre_steps: {', '.join(str(n) for n in task.pre_steps) if task.pre_steps else '-'}")
        deferred = ", ".join(str(n) for n in task.deferred_steps) if task.deferred_steps else "-"
        print(f"  deferred_steps: {deferred} -> {task.deferred_to or '-'}")
    return 0


def cmd_table(week: int) -> int:
    schedule = swarm_lib.load_schedule()
    week_entry = schedule.get_week(week)
    if week_entry is None:
        print(f"unknown week: {week}")
        return 1
    print(swarm_lib.render_table(week_entry))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    p_next = sub.add_parser("next")
    p_next.add_argument("--week", type=int, required=True)
    p_done = sub.add_parser("done")
    p_done.add_argument("stage")
    p_show = sub.add_parser("show")
    p_show.add_argument("stage")
    p_table = sub.add_parser("table")
    p_table.add_argument("--week", type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == "validate":
        return cmd_validate()
    if args.command == "next":
        return cmd_next(args.week)
    if args.command == "done":
        return cmd_done(args.stage)
    if args.command == "show":
        return cmd_show(args.stage)
    return cmd_table(args.week)


if __name__ == "__main__":
    raise SystemExit(main())
