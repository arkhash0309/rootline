from __future__ import annotations

from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.proc import run
from scripts.versions_lib import load_versions

REPO = Path(__file__).resolve().parents[2]
OBS = REPO / "deploy/charts/observability"
DEPENDENCY_KEYS = ["kube-prometheus-stack", "loki", "tempo", "opentelemetry-collector"]
HELM_ENV: dict[str, str] = {}

Docs = list[dict[str, Any]]


@pytest.fixture(scope="session")
def repo() -> Path:
    return REPO


@pytest.fixture(scope="module")
def helm_dependencies(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Fetch the observability chart dependencies once per module, with a private Helm repository config.

    Not autouse: the modules that render the observability chart select it with
    `pytestmark = pytest.mark.usefixtures("helm_dependencies")`.
    """
    helm_home = tmp_path_factory.mktemp("helm")
    HELM_ENV.update(
        {
            "HELM_REPOSITORY_CONFIG": str(helm_home / "repositories.yaml"),
            "HELM_REPOSITORY_CACHE": str(helm_home / "cache"),
            "HELM_REGISTRY_CONFIG": str(helm_home / "registry.json"),
        }
    )
    versions = load_versions()
    for key in DEPENDENCY_KEYS:
        run(["helm", "repo", "add", f"rootline-{key}", versions[key]["repo"]], env=HELM_ENV)
    run(["helm", "repo", "update"], env=HELM_ENV)
    run(["helm", "dependency", "build", str(OBS)], env=HELM_ENV, timeout=900)
    render_cached.cache_clear()
    yield


@cache
def render_cached(chart: str, env: str) -> tuple[dict[str, Any], ...]:
    namespace = "observability" if chart == "observability" else "rootline-data"
    chart_dir = REPO / f"deploy/charts/{chart}"
    args = ["helm", "template", "x", str(chart_dir), "--namespace", namespace]
    args += ["-f", str(chart_dir / "values.yaml"), "--set", f"global.env={env}"]
    env_values = chart_dir / f"values-{env}.yaml"
    if env_values.exists():
        args += ["-f", str(env_values)]
    out = run(args, env=HELM_ENV, timeout=300).stdout
    return tuple(d for d in yaml.safe_load_all(out) if d)


def tmpl(chart: str, env: str) -> Docs:
    return list(render_cached(chart, env))


def of_kind(docs: Docs, kind: str) -> Docs:
    return [d for d in docs if d["kind"] == kind]
