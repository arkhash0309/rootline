"""Render every Helm chart under deploy/ for each environment as one YAML stream (W1-T10 Step 8).

Usage: `uv run python scripts/render_manifests.py [--allow-missing]`

For each environment in ENVS (`local`, `gke`, `ci`), in that order:
1. `helm template root deploy/root --set env=<env>`;
2. for every Application of kind `local-chart` in step 1, `helm template <name> <path>` with `values.yaml`,
   `values-<env>.yaml` (when present), `--set global.env=<env>` and `--set global.domain=example.sslip.io`.
   A chart whose `Chart.yaml` lists `dependencies` and has no `charts/` directory first gets
   `helm dependency build` (network access to the chart repositories).

Output: all documents on stdout, each piece preceded by a `---` line.
Exit codes: 0 success; 1 any helm failure or a missing chart directory (message on stderr).
`--allow-missing`: a missing chart directory only prints a `skip` line on stderr (a chart that another task of
the same stage has not merged yet); every other failure still exits 1.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
ENVS = ("local", "gke", "ci")
RENDER_DOMAIN = "example.sslip.io"


class RenderError(Exception):
    """A chart could not be rendered."""


def _helm(args: list[str]) -> str:
    result = run(["helm", *args], check=False)
    if result.returncode != 0:
        raise RenderError(f"helm {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def render_root(env: str) -> str:
    return _helm(["template", "root", str(REPO / "deploy/root"), "--set", f"env={env}"])


def local_chart_apps(rendered_root: str) -> list[tuple[str, str]]:
    """(name, chart path) of every Application whose source is a Helm chart of this repository."""
    apps: list[tuple[str, str]] = []
    for doc in yaml.safe_load_all(rendered_root):
        if not doc or doc.get("kind") != "Application":
            continue
        source = doc["spec"].get("source", {})
        if source.get("repoURL", "").endswith("/rootline.git") and "helm" in source:
            apps.append((doc["metadata"]["name"], source["path"]))
    return apps


def render_local_chart(path: Path, env: str, name: str = "x") -> str:
    if not (path / "Chart.yaml").is_file():
        raise RenderError(f"chart not found: {path}")
    chart = yaml.safe_load((path / "Chart.yaml").read_text())
    if chart.get("dependencies") and not (path / "charts").is_dir():
        _helm(["dependency", "build", str(path)])
    args = ["template", name, str(path)]
    for values in (path / "values.yaml", path / f"values-{env}.yaml"):
        if values.is_file():
            args += ["-f", str(values)]
    args += ["--set", f"global.env={env}", "--set", f"global.domain={RENDER_DOMAIN}"]
    return _helm(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--allow-missing", action="store_true", help="skip chart directories that do not exist"
    )
    ns = parser.parse_args(argv)
    pieces: list[str] = []
    try:
        for env in ENVS:
            rendered = render_root(env)
            pieces.append(rendered)
            for name, rel in local_chart_apps(rendered):
                if ns.allow_missing and not (REPO / rel / "Chart.yaml").is_file():
                    print(f"skip {env} {name}: {rel} not present", file=sys.stderr)
                    continue
                pieces.append(render_local_chart(REPO / rel, env, name))
    except RenderError as exc:
        print(f"render_manifests: {exc}", file=sys.stderr)
        return 1
    for piece in pieces:
        sys.stdout.write("---\n" + piece.strip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
