"""Wait until every ArgoCD Application is Synced and Healthy (GEN-060, `task up` step 6).

Usage: uv run python scripts/wait_apps.py [--context k3d-rootline] [--timeout 1200] [--expect NAME ...]

Polls `kubectl -n argocd get applications.argoproj.io -o json` every 15 s. An Application is ready when
`.status.sync.status` is `Synced` and `.status.health.status` is `Healthy`. Each `--expect NAME` is a name
that must exist (a missing name counts as not ready); with no Application at all the pending list is
`(no Application found)`.

Exit codes: 0 every Application ready; 1 timeout (the pending names are printed, followed by the output of
`kubectl -n argocd get applications`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

POLL_S = 15
DEFAULT_CONTEXT = "k3d-rootline"
DEFAULT_TIMEOUT_S = 1200


def get_applications_json(context: str) -> str:
    result = run(
        ["kubectl", "--context", context, "-n", "argocd", "get", "applications.argoproj.io", "-o", "json"],
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def unhealthy(document: str, expected: Sequence[str]) -> list[str]:
    """Names of Applications that are not Synced/Healthy, plus `expected` names that do not exist."""
    try:
        parsed = json.loads(document)
    except json.JSONDecodeError:
        return ["(kubectl output is not JSON)"]
    items = parsed.get("items", []) if isinstance(parsed, dict) else []
    pending: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = item["metadata"]["name"]
        seen.add(name)
        status = item.get("status", {})
        sync = status.get("sync", {}).get("status", "Unknown")
        health = status.get("health", {}).get("status", "Unknown")
        if (sync, health) != ("Synced", "Healthy"):
            pending.append(name)
    pending.extend(name for name in expected if name not in seen)
    if not items and not pending:
        pending.append("(no Application found)")
    return pending


def wait_all(
    context: str,
    timeout_s: int,
    *,
    expected: Sequence[str] = (),
    get_apps: Callable[[str], str] = get_applications_json,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[str]:
    """Return the names not Synced/Healthy after `timeout_s` seconds; an empty list means success."""
    deadline = monotonic() + timeout_s
    while True:
        pending = unhealthy(get_apps(context), expected)
        if not pending:
            return []
        if monotonic() + POLL_S > deadline:
            return pending
        print(f"waiting ({len(pending)} not ready): {', '.join(pending)}", flush=True)
        sleep(POLL_S)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--context", default=DEFAULT_CONTEXT)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--expect", nargs="*", default=[])
    args = parser.parse_args(argv)
    pending = wait_all(args.context, args.timeout, expected=args.expect)
    if not pending:
        print("all applications Synced/Healthy")
        return 0
    print(f"FAIL not Synced/Healthy after {args.timeout} s: {', '.join(pending)}", file=sys.stderr)
    listing = run(["kubectl", "--context", args.context, "-n", "argocd", "get", "applications"], check=False)
    print(listing.stdout + listing.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
