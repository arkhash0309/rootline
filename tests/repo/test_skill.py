"""Verifies WIK-030."""

from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[2] / ".claude/skills/rootline-wiki/SKILL.md"


def test_skill_front_matter_and_sections() -> None:
    text = SKILL.read_text(encoding="utf-8")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm)
    assert meta["name"] == "rootline-wiki"
    for word in ("implementation", "planning", "debugging", "review"):
        assert word in meta["description"]
    for heading in (
        "## Before work",
        "## During work",
        "## After work",
        "## Rules",
        "## Templates",
    ):
        assert heading in body
    for needle in (
        "wiki/index.md",
        "wiki/status.md",
        "§0.3",
        "task wiki:lint",
        "unverified",
        "Never copy secrets",
        "WIK-020",
    ):
        assert needle in body
