"""Render the workload into rootline-env (WKL-001). Usage:
uv run python scripts/render_workload.py --out <rootline-env>/workload
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
from scripts.workload_transforms import dump, transform


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
    files = transform([d for d in yaml.safe_load_all(rendered) if d])
    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.yaml"):
        stale.unlink()
    for stem, objs in sorted(files.items()):
        (args.out / f"{stem}.yaml").write_text(dump(objs), encoding="utf-8", newline="\n")
    meta = args.out.parent / ".rootline/baseline.json"
    meta.parent.mkdir(exist_ok=True)
    meta.write_text(
        json.dumps({"baseline_tag": "baseline-v1", "rendered_from": demo["chart"]}, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
