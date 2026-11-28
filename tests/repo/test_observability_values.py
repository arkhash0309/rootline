"""Verifies WKL-020, WKL-021, WKL-022, WKL-023, ARC-002, DB-001, DB-002, PG-10, GEN-050."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import DEPENDENCY_KEYS, Docs, of_kind, tmpl

from scripts import render_versions
from scripts.versions_lib import load_versions

REPO = Path(__file__).resolve().parents[2]
OBS = REPO / "deploy/charts/observability"
PG = REPO / "deploy/charts/postgres"

# `helm_dependencies` (tests/repo/conftest.py) builds the chart dependencies once per module.
pytestmark = pytest.mark.usefixtures("helm_dependencies")


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


def test_collector_names() -> None:
    """ADR 0046 O1 and WKL-020: DaemonSet `otel-collector-agent`, Service `otel-collector` (4317, 4318)."""
    docs = tmpl("observability", "local")
    assert [d["metadata"]["name"] for d in of_kind(docs, "DaemonSet")] == ["otel-collector-agent"]
    service = next(d for d in of_kind(docs, "Service") if d["metadata"]["name"] == "otel-collector")
    assert {p["port"] for p in service["spec"]["ports"]} == {4317, 4318}
    deployments = {d["metadata"]["name"] for d in of_kind(docs, "Deployment")}
    assert not {n for n in deployments if "otel-collector" in n}


def test_collector_pipelines() -> None:
    """ADR 0046 O2 and WKL-020: component names, pipelines and file_log include patterns."""
    docs = tmpl("observability", "local")
    cm = next(d for d in of_kind(docs, "ConfigMap") if d["metadata"]["name"] == "otel-collector-agent")
    cfg = yaml.safe_load(cm["data"]["relay"])
    assert set(cfg["receivers"]) == {"file_log", "otlp"}
    assert set(cfg["processors"]) == {"batch", "k8s_attributes", "memory_limiter"}
    assert set(cfg["exporters"]) == {"otlp_grpc/tempo", "otlp_http/loki", "otlp_http/prometheus"}
    processors = ["memory_limiter", "k8s_attributes", "batch"]
    pipelines = cfg["service"]["pipelines"]
    assert pipelines["traces"] == {
        "receivers": ["otlp"],
        "processors": processors,
        "exporters": ["otlp_grpc/tempo"],
    }
    assert pipelines["metrics"] == {
        "receivers": ["otlp"],
        "processors": processors,
        "exporters": ["otlp_http/prometheus"],
    }
    assert pipelines["logs"] == {
        "receivers": ["otlp", "file_log"],
        "processors": processors,
        "exporters": ["otlp_http/loki"],
    }
    assert cfg["receivers"]["file_log"]["include"] == [
        "/var/log/pods/shop_*/*/*.log",
        "/var/log/pods/rootline_*/*/*.log",
    ]
    assert cfg["exporters"]["otlp_grpc/tempo"]["endpoint"] == "tempo.observability.svc:4317"
    assert (
        cfg["exporters"]["otlp_http/prometheus"]["endpoint"]
        == "http://prometheus-operated.observability.svc:9090/api/v1/otlp"
    )
    assert cfg["exporters"]["otlp_http/loki"]["endpoint"] == "http://loki.observability.svc:3100/otlp"


def test_collector_host_paths() -> None:
    """ADR 0046 O3 and SEC-090: one read-only hostPath /var/log/pods; hardened UID 0 container."""
    ds = next(d for d in of_kind(tmpl("observability", "local"), "DaemonSet"))
    spec = ds["spec"]["template"]["spec"]
    host_volumes = [v for v in spec["volumes"] if "hostPath" in v]
    assert [v["hostPath"] for v in host_volumes] == [{"path": "/var/log/pods", "type": "Directory"}]
    for container in spec["containers"]:
        for mount in container.get("volumeMounts", []):
            if mount["name"] == host_volumes[0]["name"]:
                assert mount["mountPath"] == "/var/log/pods" and mount["readOnly"] is True
        assert container["securityContext"] == {
            "runAsUser": 0,
            "runAsGroup": 0,
            "runAsNonRoot": False,
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "capabilities": {"drop": ["ALL"]},
            "seccompProfile": {"type": "RuntimeDefault"},
        }
    assert "/var/lib/docker/containers" not in str(spec)


def test_no_unreachable_control_plane_targets() -> None:
    """ADR 0046 O5: no Service or ServiceMonitor for components that are unreachable on k3s and GKE."""
    docs = tmpl("observability", "local")
    scraped = [d["metadata"]["name"] for d in docs if d["kind"] in ("Service", "ServiceMonitor")]
    for forbidden in ("kube-controller-manager", "kube-etcd", "kube-scheduler", "kube-proxy"):
        assert not [n for n in scraped if forbidden in n]
    monitors = [d["metadata"]["name"] for d in of_kind(docs, "ServiceMonitor")]
    for suffix in ("-kubelet", "-apiserver", "-coredns"):
        assert any(n.endswith(suffix) for n in monitors)


def _pod_specs(docs: Docs) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (workload name, pod spec) for every workload kind in `docs`."""
    for d in docs:
        if d["kind"] in ("Deployment", "DaemonSet", "StatefulSet"):
            yield d["metadata"]["name"], d["spec"]["template"]["spec"]
        elif d["kind"] == "Pod":
            yield d["metadata"]["name"], d["spec"]


def test_no_host_ports_and_no_jaeger_zipkin_ports() -> None:
    """ARC-010 and WKL-020: PSS `baseline` (warn and audit on `observability`) forbids hostPort, so no
    container port has a non-zero hostPort; the collector exposes only OTLP ports 4317 and 4318."""
    docs = tmpl("observability", "local")
    all_ports: list[tuple[str, int, str]] = []
    for workload, spec in _pod_specs(docs):
        for container in spec.get("containers", []) + spec.get("initContainers", []):
            for port in container.get("ports", []):
                assert port.get("hostPort", 0) == 0, f"{workload}/{container['name']}: {port}"
                all_ports.append((workload, port["containerPort"], port.get("name", "")))
    collector_ports = {(n, p) for w, p, n in all_ports if w == "otel-collector-agent"}
    assert collector_ports == {("otlp", 4317), ("otlp-http", 4318)}
    assert not {p for w, p, _ in all_ports if w == "otel-collector-agent"} & {6831, 14250, 14268, 9411}
    service_ports = {
        port["port"]
        for d in of_kind(docs, "Service")
        if d["metadata"]["name"] == "otel-collector"
        for port in d["spec"]["ports"]
    }
    assert service_ports == {4317, 4318}


def test_loki_rules_sidecar_disabled() -> None:
    """ARC-030: the Loki rules sidecar is not rendered (it is outside the memory budget)."""
    for d in tmpl("observability", "local"):
        if d["metadata"]["name"] == "loki" and d["kind"] == "StatefulSet":
            names = [c["name"] for c in d["spec"]["template"]["spec"]["containers"]]
            assert names == ["loki"]
            break
    else:
        pytest.fail("Loki StatefulSet not rendered")


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


def _flatten_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Return the selector, direction, peers and ports of a single-rule NetworkPolicy."""
    spec = policy["spec"]
    direction = "ingress" if "ingress" in spec else "egress"
    (rule,) = spec[direction]
    return {
        "selector": spec["podSelector"].get("matchLabels", {}),
        "direction": direction,
        "peers": rule.get("from", rule.get("to")),
        "ports": [p["port"] for p in rule.get("ports", [])],
    }


def _ns(*names: str) -> list[dict[str, Any]]:
    return [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": n}}} for n in names]


def test_observability_network_policies() -> None:
    """ADR 0046 O4 and ARC-010: the eight allow-rules of the default-deny observability namespace."""
    policies = {p["metadata"]["name"]: p for p in of_kind(tmpl("observability", "local"), "NetworkPolicy")}
    assert {p["metadata"]["namespace"] for p in policies.values()} == {"observability"}
    assert set(policies) == {
        "allow-same-namespace",
        "allow-otlp-ingress",
        "allow-query-ingress",
        "allow-alertmanager-ingress",
        "allow-operator-webhook-ingress",
        "allow-egress-pods",
        "allow-egress-apiserver",
        "allow-egress-kubelet",
    }
    collector = {"app.kubernetes.io/name": "opentelemetry-collector", "component": "agent-collector"}
    operator = {"app.kubernetes.io/name": "kube-prometheus-stack-prometheus-operator"}
    anywhere = [{"ipBlock": {"cidr": "0.0.0.0/0"}}]
    expected = {
        "allow-same-namespace": ({}, "ingress", [{"podSelector": {}}], []),
        "allow-otlp-ingress": (collector, "ingress", [{"namespaceSelector": {}}], [4317, 4318]),
        "allow-query-ingress": ({}, "ingress", _ns("rootline", "observability"), [9090, 3100, 3200]),
        "allow-alertmanager-ingress": ({}, "ingress", _ns("observability"), [9093]),
        "allow-operator-webhook-ingress": (operator, "ingress", anywhere, [10250]),
        "allow-egress-pods": ({}, "egress", [{"namespaceSelector": {}}], []),
        "allow-egress-apiserver": ({}, "egress", anywhere, [443, 6443]),
        "allow-egress-kubelet": ({"app.kubernetes.io/name": "prometheus"}, "egress", anywhere, [10250]),
    }
    for name, (selector, direction, peers, ports) in expected.items():
        flat = _flatten_policy(policies[name])
        assert flat == {"selector": selector, "direction": direction, "peers": peers, "ports": ports}, name
    egress_10250 = [
        name
        for name, p in policies.items()
        if any(
            port["port"] == 10250 for rule in p["spec"].get("egress", []) for port in rule.get("ports", [])
        )
    ]
    assert egress_10250 == ["allow-egress-kubelet"]


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
    """ADR 0046 O4 and DB-001: 5432 from rootline and keycloak; cnpg-system on 8000 and 5432."""
    policies = of_kind(tmpl("postgres", "local"), "NetworkPolicy")
    assert {p["metadata"]["name"] for p in policies} == {
        "allow-postgres-clients",
        "allow-cnpg-operator",
        "allow-same-namespace",
        "allow-egress-apiserver",
    }
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


def test_render_versions_chart_keys() -> None:
    """ADR 0046 T1, T11 and GEN-050: operator CRDs row in the root chart; platform-config output."""
    versions = load_versions()
    root = yaml.safe_load((REPO / "deploy/root/files/versions.yaml").read_text(encoding="utf-8"))
    assert root["prometheus-operator-crds"] == versions["prometheus-operator-crds"]
    out = render_versions.render()
    path = REPO / "deploy/charts/platform-config/files/versions.yaml"
    assert (path in out) == (REPO / "deploy/charts/platform-config/Chart.yaml").exists()
    if path in out:
        assert yaml.safe_load(out[path]) == {"kubectl-image": versions["kubectl-image"]}
