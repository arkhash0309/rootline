"""Verifies WIK-020, WIK-021."""

from datetime import date
from pathlib import Path

import pytest

from scripts import wiki_lint as wl


def make_wiki(root: Path) -> Path:
    w = root / "wiki"
    (w / "adr").mkdir(parents=True)
    (w / "components").mkdir()
    for n in range(1, 26):
        (w / "adr" / f"{n:04d}-x.md").write_text("# ADR\n", encoding="utf-8")
    (w / "adr" / "0000-template.md").write_text("# T\n", encoding="utf-8")
    for slug in wl.COMPONENT_PAGES:
        (w / "components" / f"{slug}.md").write_text("# C\n", encoding="utf-8")
    files = sorted(p.relative_to(w).as_posix() for p in w.rglob("*.md"))
    index = "# Index\n" + "".join(f"- [{f}]({f})\n" for f in [*files, "index.md", "status.md"])
    (w / "index.md").write_text(index, encoding="utf-8")
    (w / "status.md").write_text(
        f"# Status\nLast updated: {date.today():%Y-%m-%d} (commit abc1234)\n",
        encoding="utf-8",
    )
    return w


def test_clean_wiki_passes(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    assert wl.check_static(w, today=date.today()) == []


def test_missing_component_page(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "gate.md").unlink()
    assert "missing-component: gate" in wl.check_static(w, today=date.today())


def test_missing_adr(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "adr" / "0007-x.md").unlink()
    assert "missing-adr: 0007" in wl.check_static(w, today=date.today())


@pytest.mark.parametrize("word", ["TODO", "TBD"])
def test_forbidden_words(tmp_path: Path, word: str) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "api.md").write_text(f"# C\n{word} later\n", encoding="utf-8")
    assert f"forbidden-word: components/api.md: {word}" in wl.check_static(w, today=date.today())


def test_broken_relative_link(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "api.md").write_text("[x](../nope.md)\n", encoding="utf-8")
    assert "broken-link: components/api.md -> ../nope.md" in wl.check_static(w, today=date.today())


def test_index_must_list_every_file(tmp_path: Path) -> None:
    w = make_wiki(tmp_path)
    (w / "components" / "extra.md").write_text("# E\n", encoding="utf-8")
    assert "index-missing: components/extra.md" in wl.check_static(w, today=date.today())


def test_changed_files_rule_requires_wiki_change() -> None:
    assert wl.check_changed(["services/api/x.py"], pr_body="") == ["wiki-not-updated: services/api/x.py"]
    assert wl.check_changed(["services/api/x.py", "wiki/log.md"], pr_body="") == []
    assert wl.check_changed(["services/api/x.py"], pr_body="wiki-skip: typo only\n") == []
    assert wl.check_changed(["README.md"], pr_body="") == []


def test_status_staleness() -> None:
    assert wl.status_is_stale(status_date=date(2026, 12, 1), latest_code_commit=date(2026, 12, 9))
    assert not wl.status_is_stale(status_date=date(2026, 12, 3), latest_code_commit=date(2026, 12, 9))
