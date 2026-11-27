"""Validate versions.yaml against the GEN-050 version lines.

Usage: uv run python scripts/check_versions.py
Exit codes: 0 every key is present and satisfies its line; 1 at least one error (one stderr line per
error, format `<key>: <problem>`); 2 versions.yaml is missing or is not a mapping (one stderr line).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.versions_lib import load_versions, validate


def main() -> int:
    try:
        data = load_versions()
    except (OSError, ValueError) as exc:
        print(f"versions.yaml: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
