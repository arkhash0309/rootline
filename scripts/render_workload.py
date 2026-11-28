"""Render the workload into rootline-env (WKL-001). Usage:
  uv run python scripts/render_workload.py --out <rootline-env>/workload
Exit codes: 0 written; 3 a kept workload references an object missing from the output (PG-25 D3),
nothing written. A failing helm command raises subprocess.CalledProcessError (exit 1).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run
from scripts.versions_lib import REPO, load_versions
from scripts.workload_transforms import UnresolvedReferenceError, dump, transform

# WKL-001, GEN-011, PG-29 (ADR 0048 D3): the rootline-env tag of this render; +1 on every re-render.
BASELINE_TAG = "baseline-v2"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    demo = load_versions()["opentelemetry-demo"]
    run(["helm", "repo", "add", "open-telemetry", demo["repo"], "--force-update"])
    rendered = run(
        [
            "helm",
            "template",
            "shop",
            "open-telemetry/opentelemetry-demo",
            "--version",
            demo["chart"],
            "--namespace",
            "shop",
            "-f",
            str(REPO / "deploy/upstream/otel-demo/values.yaml"),
        ]
    ).stdout
    try:
        files = transform([d for d in yaml.safe_load_all(rendered) if d])
    except UnresolvedReferenceError as exc:  # PG-25 D3: report every error, write nothing
        for line in exc.errors:
            print(f"render_workload: {line}", file=sys.stderr)
        return 3
    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.yaml"):
        stale.unlink()
    for stem, objs in sorted(files.items()):
        (args.out / f"{stem}.yaml").write_text(dump(objs), encoding="utf-8", newline="\n")
    meta = args.out.parent / ".rootline/baseline.json"
    meta.parent.mkdir(exist_ok=True)
    meta.write_text(
        json.dumps({"baseline_tag": BASELINE_TAG, "rendered_from": demo["chart"]}, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
