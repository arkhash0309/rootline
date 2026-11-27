"""Verifies GEN-050."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.versions_lib import CONSTRAINTS, load_versions, validate, version_of

REPO = Path(__file__).resolve().parents[2]


def test_every_spec_key_present() -> None:
    data = load_versions(REPO / "versions.yaml")
    missing = [k for k in CONSTRAINTS if k not in data]
    assert missing == []


def test_every_value_satisfies_its_line() -> None:
    assert validate(load_versions(REPO / "versions.yaml")) == []


def test_pin_date_format() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", load_versions(REPO / "versions.yaml")["pin_date"])


def test_validate_reports_bad_value() -> None:
    data = {"pin_date": "2026-11-30", "python": "3.11.9"}
    errors = validate(data, keys=["python"])
    assert errors == ["python: '3.11.9' does not match ^3\\.12\\.\\d+$"]


def test_version_of_mapping() -> None:
    assert version_of("x", {"x": {"version": "1.2.3", "digest": "sha256:" + "a" * 64}}) == "1.2.3"


def test_check_versions_script_passes() -> None:
    r = subprocess.run([sys.executable, "scripts/check_versions.py"], cwd=REPO)
    assert r.returncode == 0


def test_check_versions_invalid_yaml_exits_2(tmp_path: Path) -> None:
    """Verifies GEN-050: invalid YAML gives exit 2 and one stderr line `versions.yaml: ...`."""
    (tmp_path / "scripts").mkdir()
    for name in ("__init__.py", "check_versions.py", "versions_lib.py"):
        shutil.copy(REPO / "scripts" / name, tmp_path / "scripts" / name)
    (tmp_path / "versions.yaml").write_text("a: [1, 2\nb: :\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "scripts/check_versions.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    lines = r.stderr.splitlines()
    assert r.returncode == 2
    assert len(lines) == 1
    assert lines[0].startswith("versions.yaml:")


def test_generated_files_up_to_date() -> None:
    r = subprocess.run([sys.executable, "scripts/render_versions.py", "--check"], cwd=REPO)
    assert r.returncode == 0
