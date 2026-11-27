"""Run a command only when a path exists (W1-T06): run_if_exists.py <path> -- <cmd...>.

Exit codes: 0 when the path is missing (prints `skip: <path> missing`) or the command exits 0;
the command's own exit code otherwise; 2 on a usage error.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--":
        print("usage: run_if_exists.py <path> -- <cmd...>", file=sys.stderr)
        return 2
    path, cmd = argv[0], argv[2:]
    if not Path(path).exists():
        print(f"skip: {path} missing")
        return 0
    return run(cmd, check=False, capture=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
