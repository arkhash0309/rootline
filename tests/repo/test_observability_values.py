"""Verifies WKL-020, WKL-021, WKL-022, WKL-023, ARC-002, DB-001, DB-002, PG-10, GEN-050."""

from __future__ import annotations

from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import render_versions
from scripts.proc import run
from scripts.versions_lib import load_versions

REPO = Path(__file__).resolve().parents[2]
OBS = REPO / "deploy/charts/observability"
PG = REPO / "deploy/charts/postgres"
DEPENDENCY_KEYS = ["kube-prometheus-stack", "loki", "tempo", "opentelemetry-collector"]
HELM_ENV: dict[str, str] = {}

Docs = list[dict[str, Any]]


@pytest.fixture(scope="module", autouse=True)
def helm_dependencies(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Fetch the observability chart dependencies once, with a private Helm repository config."""
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


# The collector chart 0.183.2 rewrites component ids to the canonical names of collector 0.165
# (aliases of the names used in spec WKL-020). Tests compare using the spec names.
CANONICAL_ALIASES = {
    "otlp_grpc": "otlp",
    "otlp_http": "otlphttp",
    "k8s_attributes": "k8sattributes",
    "file_log": "filelog",
}


def canonical_component_ids(node: Any) -> Any:
    """Return `node` with every component id (dict key or list item) mapped to its spec name."""
    if isinstance(node, dict):
        return {_spec_id(k): canonical_component_ids(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_spec_id(v) if isinstance(v, str) else canonical_component_ids(v) for v in node]
    return node


def _spec_id(component_id: str) -> str:
    kind, sep, name = component_id.partition("/")
    return CANONICAL_ALIASES.get(kind, kind) + sep + name


def tmpl(chart: str, env: str) -> Docs:
    return list(render_cached(chart, env))


def of_kind(docs: Docs, kind: str) -> Docs:
    return [d for d in docs if d["kind"] == kind]


def test_prometheus_otlp_and_retention() -> None:
    """WKL-021 and WKL-023: OTLP receiver, promoted attributes, 15 s scrape, 2 d retention locally."""
    prom = next(d for d in tmpl("observability", "local") if d["kind"] == "Prometheus")
    assert "otlp-write-receiver" in prom["spec"].get("enableFeatures", []) or (
        prom["spec"].get("enableOTLPReceiver") is True
    )
    assert prom["spec"]["retention"] == "2d"
    assert set(prom["spec"]["otlp"]["promoteResourceAttributes"]) >= {
        "service.name",
        "k8s.namespace.name",
        "k8s.pod.name",
    }
    assert prom["spec"]["scrapeInterval"] == "15s"


def test_gke_retention() -> None:
    """WKL-023: Prometheus 1 d, Loki 24 h, Tempo 24 h on gke."""
    docs = tmpl("observability", "gke")
    prom = next(d for d in docs if d["kind"] == "Prometheus")
    assert prom["spec"]["retention"] == "1d"
    loki_cfg = next(d for d in of_kind(docs, "ConfigMap") if d["metadata"]["name"] == "loki")
    assert "retention_period: 24h" in loki_cfg["data"]["config.yaml"]
    tempo_cfg = next(d for d in of_kind(docs, "ConfigMap") if d["metadata"]["name"] == "tempo")
    assert "block_retention: 24h" in tempo_cfg["data"]["tempo.yaml"]


def test_local_loki_and_tempo_retention() -> None:
    """WKL-023: Loki and Tempo keep 48 h locally."""
    docs = tmpl("observability", "local")
    loki_cfg = next(d for d in of_kind(docs, "ConfigMap") if d["metadata"]["name"] == "loki")
    assert "retention_period: 48h" in loki_cfg["data"]["config.yaml"]
    tempo_cfg = next(d for d in of_kind(docs, "ConfigMap") if d["metadata"]["name"] == "tempo")
    assert "block_retention: 48h" in tempo_cfg["data"]["tempo.yaml"]


def test_ci_profile_disables_loki_tempo_collector() -> None:
    """The ci profile keeps only Prometheus (6 h retention) and Alertmanager."""
    docs = tmpl("observability", "ci")
    names = {d["metadata"]["name"] for d in docs}
    assert not any(n in names for n in ("loki", "tempo", "otel-collector"))
    prom = next(d for d in docs if d["kind"] == "Prometheus")
    assert prom["spec"]["retention"] == "6h"


def test_no_grafana() -> None:
    """ARC-002: Grafana is not deployed."""
    for env in ("local", "gke", "ci"):
        names = {(d["kind"], d["metadata"]["name"]) for d in tmpl("observability", env)}
        assert not any("grafana" in n for _, n in names)


def test_collector_pipelines() -> None:
    """WKL-020: collector Service name, DaemonSet, pipelines and filelog include patterns."""
    docs = tmpl("observability", "local")
    names = {(d["kind"], d["metadata"]["name"]) for d in docs}
    assert {("Service", "otel-collector"), ("DaemonSet", "otel-collector-agent")} <= names
    cm = next(d for d in of_kind(docs, "ConfigMap") if d["metadata"]["name"] == "otel-collector-agent")
    cfg = canonical_component_ids(yaml.safe_load(cm["data"]["relay"]))
    pipelines = cfg["service"]["pipelines"]
    assert pipelines["traces"]["exporters"] == ["otlp/tempo"]
    assert pipelines["metrics"]["exporters"] == ["otlphttp/prometheus"]
    assert pipelines["logs"]["exporters"] == ["otlphttp/loki"]
    for name in ("traces", "metrics", "logs"):
        assert pipelines[name]["processors"][0] == "memory_limiter"
        assert "k8sattributes" in pipelines[name]["processors"]
        assert pipelines[name]["processors"][-1] == "batch"
    assert pipelines["logs"]["receivers"] == ["otlp", "filelog"]
    assert cfg["receivers"]["filelog"]["include"] == [
        "/var/log/pods/shop_*/*/*.log",
        "/var/log/pods/rootline_*/*/*.log",
    ]
    assert cfg["exporters"]["otlp/tempo"]["endpoint"] == "tempo.observability.svc:4317"
    assert (
        cfg["exporters"]["otlphttp/prometheus"]["endpoint"]
        == "http://prometheus-operated.observability.svc:9090/api/v1/otlp"
    )
    assert cfg["exporters"]["otlphttp/loki"]["endpoint"] == "http://loki.observability.svc:3100/otlp"


def test_service_dns_names() -> None:
    """WKL-020: Services are named loki, tempo and otel-collector (DNS names in the exporters)."""
    services = {d["metadata"]["name"] for d in of_kind(tmpl("observability", "local"), "Service")}
    assert {"loki", "tempo", "otel-collector"} <= services


def test_tempo_metrics_generator() -> None:
    """WKL-022: span-metrics and service-graphs remote-write to Prometheus."""
    cm = next(
        d for d in of_kind(tmpl("observability", "local"), "ConfigMap") if d["metadata"]["name"] == "tempo"
    )
    cfg = yaml.safe_load(cm["data"]["tempo.yaml"])
    gen = cfg["metrics_generator"]
    assert gen["storage"]["remote_write"][0]["url"] == (
        "http://prometheus-operated.observability.svc:9090/api/v1/write"
    )
    assert set(cfg["overrides"]["defaults"]["metrics_generator"]["processors"]) == {
        "service-graphs",
        "span-metrics",
    }


def test_observability_network_policies() -> None:
    """ARC-010: allow-rules for the default-deny observability namespace."""
    policies = of_kind(tmpl("observability", "local"), "NetworkPolicy")
    assert policies
    assert {p["metadata"]["namespace"] for p in policies} == {"observability"}
    ingress_ports = {
        port["port"]
        for p in policies
        for rule in p["spec"].get("ingress", [])
        for port in rule.get("ports", [])
    }
    assert ingress_ports >= {4317, 4318, 9090, 3100, 3200, 9093}
    egress_ports = {
        port["port"]
        for p in policies
        for rule in p["spec"].get("egress", [])
        for port in rule.get("ports", [])
    }
    assert egress_ports >= {443, 6443}


def test_dependency_versions_match_versions_yaml() -> None:
    """GEN-050: Chart.yaml dependencies carry the chart versions of versions.yaml."""
    versions = load_versions()
    chart = yaml.safe_load((OBS / "Chart.yaml").read_text(encoding="utf-8"))
    deps = {d["name"]: d for d in chart["dependencies"]}
    assert list(deps) == DEPENDENCY_KEYS
    for key in DEPENDENCY_KEYS:
        assert deps[key]["version"] == versions[key]["chart"]
        assert deps[key]["repository"] == versions[key]["repo"]
    for key in ("loki", "tempo", "opentelemetry-collector"):
        assert deps[key]["condition"] == f"{key}.enabled"


def test_chart_lock_matches_chart_yaml() -> None:
    """GEN-050: Chart.lock lists the same dependency versions as Chart.yaml (run `helm dependency update`)."""
    chart = yaml.safe_load((OBS / "Chart.yaml").read_text(encoding="utf-8"))
    lock = yaml.safe_load((OBS / "Chart.lock").read_text(encoding="utf-8"))
    assert [(d["name"], d["version"]) for d in lock["dependencies"]] == [
        (d["name"], d["version"]) for d in chart["dependencies"]
    ]


def test_render_versions_rewrites_and_checks_chart_dependencies() -> None:
    """GEN-050: render_versions covers observability/Chart.yaml (rewrite and --check)."""
    versions = load_versions()
    path = OBS / "Chart.yaml"
    stale = path.read_text(encoding="utf-8").replace(
        f'version: "{versions["loki"]["chart"]}"', 'version: "0.0.1"'
    )
    assert stale != path.read_text(encoding="utf-8")
    assert render_versions.render()[path] == path.read_text(encoding="utf-8")
    assert render_versions.rewrite_chart_dependencies(stale, versions) == path.read_text(encoding="utf-8")


def test_cnpg_cluster() -> None:
    """DB-001: cluster rootline-pg in rootline-data, parameters, initdb bootstrap."""
    c = next(d for d in tmpl("postgres", "local") if d["kind"] == "Cluster")
    assert c["metadata"]["name"] == "rootline-pg"
    assert c["metadata"]["namespace"] == "rootline-data"
    assert c["spec"]["instances"] == 1 and c["spec"]["storage"]["size"] == "5Gi"
    assert c["spec"]["storage"]["storageClass"] == "local-path"
    assert c["spec"]["postgresql"]["parameters"] == {
        "shared_buffers": "128MB",
        "max_connections": "100",
        "log_min_duration_statement": "500",
    }
    assert c["spec"]["bootstrap"]["initdb"] == {
        "database": "rootline",
        "owner": "rootline_migrator",
        "secret": {"name": "pg-rootline-migrator"},
    }
    assert c["spec"]["resources"] == {"requests": {"memory": "384Mi"}, "limits": {"memory": "768Mi"}}


def test_cnpg_image_pinned_by_digest() -> None:
    """DB-001 and GEN-050: imageName is `<repo>:<version>@<digest>` of versions.yaml `postgres-image`."""
    pin = load_versions()["postgres-image"]
    c = next(d for d in tmpl("postgres", "local") if d["kind"] == "Cluster")
    assert c["spec"]["imageName"] == f"{pin['repo']}:{pin['version']}@{pin['digest']}"


def test_cnpg_gke_storage_class() -> None:
    """DB-001: standard-rwo on gke."""
    c = next(d for d in tmpl("postgres", "gke") if d["kind"] == "Cluster")
    assert c["spec"]["storage"]["storageClass"] == "standard-rwo"


def test_cnpg_managed_roles() -> None:
    """DB-002 and PG-10: six login roles whose password Secrets are `pg-<role>` (not generated here)."""
    c = next(d for d in tmpl("postgres", "local") if d["kind"] == "Cluster")
    roles = {r["name"]: r for r in c["spec"]["managed"]["roles"]}
    assert set(roles) == {
        "rootline_migrator",
        "rootline_api",
        "rootline_agent",
        "rootline_faultlab",
        "rootline_console",
        "keycloak",
    }
    for name, role in roles.items():
        assert role["ensure"] == "present" and role["login"] is True
        assert role["passwordSecret"] == {"name": "pg-" + name.replace("_", "-")}
    kinds = {d["kind"] for d in tmpl("postgres", "local")}
    assert "Secret" not in kinds


def test_keycloak_database() -> None:
    """DB-001: database keycloak owned by role keycloak."""
    db = next(d for d in tmpl("postgres", "local") if d["kind"] == "Database")
    assert db["metadata"]["name"] == "keycloak"
    assert db["metadata"]["namespace"] == "rootline-data"
    assert db["spec"]["name"] == "keycloak"
    assert db["spec"]["owner"] == "keycloak"
    assert db["spec"]["cluster"] == {"name": "rootline-pg"}


def test_postgres_network_policies() -> None:
    """ARC-010: 5432 from rootline and keycloak; operator namespace cnpg-system on 8000 and 5432."""
    policies = of_kind(tmpl("postgres", "local"), "NetworkPolicy")
    assert policies
    assert {p["metadata"]["namespace"] for p in policies} == {"rootline-data"}
    sources: dict[str, set[int]] = {}
    for p in policies:
        for rule in p["spec"].get("ingress", []):
            for peer in rule.get("from", []):
                ns = (
                    peer.get("namespaceSelector", {})
                    .get("matchLabels", {})
                    .get("kubernetes.io/metadata.name")
                )
                if ns:
                    sources.setdefault(ns, set()).update(port["port"] for port in rule["ports"])
    assert sources == {"rootline": {5432}, "keycloak": {5432}, "cnpg-system": {8000, 5432}}
    egress_ports = {
        port["port"]
        for p in policies
        for rule in p["spec"].get("egress", [])
        for port in rule.get("ports", [])
    }
    assert egress_ports >= {443, 6443}
