"""`task images` (GEN-060): build every service image and load it into a local cluster.

Usage: uv run python scripts/build_images.py --tag <t>
       (--import-k3d <cluster> | --load-kind <cluster> | --push <registry>)

Image list `SERVICES`: the directory name of every `services/*/Dockerfile`, plus `console` when
`apps/console/Dockerfile` exists. For each image: `docker buildx build --load -f <Dockerfile>
-t rootline/<name>:<tag> --build-arg PYTHON_IMAGE=... --build-arg UV_IMAGE=...
--build-arg NODE_IMAGE=... <repo root>`
(base images are `repo@digest` rows of `versions.yaml`). Then, by mode: `k3d image import -c <cluster>`,
`kind load docker-image --name <cluster>`, or `docker tag` + `docker push <registry>/rootline/<name>:<tag>`.

Exit codes: 0 success or no image has a Dockerfile (message printed, nothing built); 1 any command failed.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
BASE_IMAGE_ARGS = {"PYTHON_IMAGE": "python-image", "UV_IMAGE": "uv-image", "NODE_IMAGE": "node-image"}


def discover_services(repo: Path = REPO) -> list[str]:
    names = sorted(p.parent.name for p in repo.glob("services/*/Dockerfile"))
    if (repo / "apps/console/Dockerfile").exists():
        names.append("console")
    return names


SERVICES: list[str] = discover_services()


def dockerfile_of(name: str, repo: Path) -> Path:
    return repo / ("apps/console/Dockerfile" if name == "console" else f"services/{name}/Dockerfile")


def build_args(versions: Mapping[str, Any], mapping: Mapping[str, str] = BASE_IMAGE_ARGS) -> list[str]:
    out: list[str] = []
    for arg, key in mapping.items():
        row = versions[key]
        out += ["--build-arg", f"{arg}={row['repo']}@{row['digest']}"]
    return out


def build_command(name: str, tag: str, repo: Path, args: Sequence[str]) -> list[str]:
    return [
        "docker",
        "buildx",
        "build",
        "--load",
        "-f",
        str(dockerfile_of(name, repo)),
        "-t",
        f"rootline/{name}:{tag}",
        *args,
        str(repo),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tag", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--import-k3d", metavar="CLUSTER")
    mode.add_argument("--load-kind", metavar="CLUSTER")
    mode.add_argument("--push", metavar="REGISTRY")
    args = parser.parse_args(argv)
    if not SERVICES:
        print("no image has a Dockerfile yet: nothing to build")
        return 0
    versions = yaml.safe_load((REPO / "versions.yaml").read_text(encoding="utf-8"))
    extra = build_args(versions)
    refs = [f"rootline/{name}:{args.tag}" for name in SERVICES]
    for name in SERVICES:
        print(f"==> build rootline/{name}:{args.tag}", flush=True)
        if run(
            build_command(name, args.tag, REPO, extra), check=False, capture=False, timeout=3600
        ).returncode:
            print(f"FAIL build {name}", file=sys.stderr)
            return 1
    if args.import_k3d:
        commands = [["k3d", "image", "import", "-c", args.import_k3d, *refs]]
    elif args.load_kind:
        commands = [["kind", "load", "docker-image", "--name", args.load_kind, *refs]]
    else:
        commands = []
        for ref in refs:
            remote = f"{args.push}/{ref}"
            commands += [["docker", "tag", ref, remote], ["docker", "push", remote]]
    for command in commands:
        print(f"==> {' '.join(command)}", flush=True)
        if run(command, check=False, capture=False, timeout=1800).returncode:
            print(f"FAIL {' '.join(command)}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
