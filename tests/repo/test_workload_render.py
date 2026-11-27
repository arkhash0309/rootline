"""Verifies WKL-010, WKL-011 (TST-WKL-001), PG-11, PG-12."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import scripts.render_workload as render_workload
from scripts.workload_transforms import COLLECTOR_FQDN, KEPT_COMPONENTS, dump, transform

FIX = Path(__file__).parent / "fixtures/otel-demo-mini.yaml"


def docs() -> list[dict[str, Any]]:
    return [d for d in yaml.safe_load_all(FIX.read_text(encoding="utf-8")) if d]


def deployment(component: str) -> dict[str, Any]:
    return next(o for o in transform(docs())[component] if o["kind"] == "Deployment")


def env_of(container: dict[str, Any]) -> dict[str, Any]:
    return {e["name"]: e.get("value") for e in container["env"]}


def test_tst_wkl_001_deterministic() -> None:
    """TST-WKL-001: two renders are byte-identical (WKL-011)."""
    a = {k: dump(v) for k, v in transform(docs()).items()}
    b = {k: dump(v) for k, v in transform(docs()).items()}
    assert a == b


def test_transform_does_not_mutate_input() -> None:
    """WKL-011: transform is a pure function of its input."""
    original = docs()
    snapshot = copy.deepcopy(original)
    transform(original)
    assert original == snapshot


def test_namespace_and_no_secrets() -> None:
    """WKL-010 steps 1 and 2."""
    out = transform(docs())
    objs = [o for v in out.values() for o in v]
    assert all(o["metadata"]["namespace"] == "shop" for o in objs)
    assert not any(o["kind"] == "Secret" for o in objs)


def test_only_kept_components_remain() -> None:
    """WKL-002: objects of components outside the kept list are dropped."""
    out = transform(docs())
    assert "jaeger" not in out
    assert set(out) - {"flagd-config", "networkpolicies"} <= set(KEPT_COMPONENTS)
    assert len(KEPT_COMPONENTS) == 19


def test_component_files_sorted_by_kind_then_name() -> None:
    """WKL-010 step 8."""
    kinds = [o["kind"] for o in transform(docs())["payment"]]
    assert kinds == ["ServiceAccount", "Service", "Deployment"]


def test_labels_on_workloads() -> None:
    """WKL-010 step 3."""
    dep = deployment("payment")
    assert dep["metadata"]["labels"]["app.kubernetes.io/part-of"] == "rootline-workload"
    assert dep["spec"]["template"]["metadata"]["labels"]["rootline.dev/workload"] == "payment"


def test_readiness_probe_added() -> None:
    """WKL-010 step 4."""
    probe = deployment("payment")["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
    assert probe == {
        "tcpSocket": {"port": 8080},
        "initialDelaySeconds": 5,
        "periodSeconds": 10,
        "failureThreshold": 3,
    }


def test_existing_readiness_probe_is_kept() -> None:
    """WKL-010 step 4: a container that already has a readinessProbe keeps it."""
    source = docs()
    dep = next(d for d in source if d["kind"] == "Deployment" and d["metadata"]["name"] == "payment")
    existing = {"httpGet": {"path": "/healthz", "port": 8080}}
    dep["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = existing
    out = next(o for o in transform(source)["payment"] if o["kind"] == "Deployment")
    assert out["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] == existing


def test_collector_name_rewritten_ports_kept() -> None:
    """WKL-010 step 5, PG-12."""
    env = env_of(deployment("payment")["spec"]["template"]["spec"]["containers"][0])
    assert env["OTEL_COLLECTOR_NAME"] == COLLECTOR_FQDN
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://$(OTEL_COLLECTOR_NAME):4317"


def test_endpoint_without_collector_name_gets_fqdn_and_keeps_port() -> None:
    """PG-12: an endpoint without $(OTEL_COLLECTOR_NAME) gets the FQDN host, same scheme and port."""
    env = env_of(deployment("load-generator")["spec"]["template"]["spec"]["containers"][0])
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == f"http://{COLLECTOR_FQDN}:4318"


def test_flagd_mounts_configmap_directly() -> None:
    """WKL-010 step 6, PG-11."""
    spec = deployment("flagd")["spec"]["template"]["spec"]
    assert [c["name"] for c in spec.get("initContainers", [])] == []
    assert [c["name"] for c in spec["containers"]] == ["flagd"]
    vols = {v["name"]: v for v in spec["volumes"]}
    assert vols["config-rw"] == {"name": "config-rw", "configMap": {"name": "flagd-config"}}
    assert "config-ro" not in vols
    mounts = {m["name"]: m["mountPath"] for m in spec["containers"][0]["volumeMounts"]}
    assert mounts == {"config-rw": "/etc/flagd"}


def test_flags_all_off() -> None:
    """WKL-010 step 6: every flag's defaultVariant is off."""
    cm = transform(docs())["flagd-config"][0]
    flags = json.loads(cm["data"]["demo.flagd.json"])["flags"]
    assert {f["defaultVariant"] for f in flags.values()} == {"off"}
    assert cm["metadata"]["namespace"] == "shop"


def test_load_generator_env() -> None:
    """WKL-010 step 7."""
    env = env_of(deployment("load-generator")["spec"]["template"]["spec"]["containers"][0])
    assert (env["LOCUST_USERS"], env["LOCUST_SPAWN_RATE"], env["LOCUST_AUTOSTART"]) == ("10", "2", "true")


def test_networkpolicies_file() -> None:
    """WKL-010 step 9."""
    policies = transform(docs())["networkpolicies"]
    assert [o["metadata"]["name"] for o in policies] == ["allow-observability-scrape", "allow-same-namespace"]
    scrape = policies[0]["spec"]["ingress"][0]["from"][0]["namespaceSelector"]
    assert scrape == {"matchLabels": {"kubernetes.io/metadata.name": "observability"}}


def test_dump_is_sorted_yaml_stream() -> None:
    """WKL-010 step 8: keys sorted, documents separated by a --- line."""
    text = dump(transform(docs())["networkpolicies"])
    loaded = [d for d in yaml.safe_load_all(text) if d]
    assert [d["kind"] for d in loaded] == ["NetworkPolicy", "NetworkPolicy"]
    assert text.index("apiVersion:") < text.index("kind:") < text.index("metadata:")


class _Result:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_render_workload_writes_files_and_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-001, WKL-011: one file per stem, stale files removed, baseline.json written."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: Any) -> _Result:
        calls.append(cmd)
        return _Result(FIX.read_text(encoding="utf-8"))

    monkeypatch.setattr(render_workload, "run", fake_run)
    out = tmp_path / "env/workload"
    out.mkdir(parents=True)
    (out / "stale.yaml").write_text("x: 1\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["render_workload.py", "--out", str(out)])

    assert render_workload.main() == 0
    first = {p.name: p.read_bytes() for p in out.glob("*.yaml")}
    assert render_workload.main() == 0
    second = {p.name: p.read_bytes() for p in out.glob("*.yaml")}

    assert first == second
    assert sorted(first) == [
        "flagd-config.yaml",
        "flagd.yaml",
        "load-generator.yaml",
        "networkpolicies.yaml",
        "payment.yaml",
    ]
    baseline = json.loads((out.parent / ".rootline/baseline.json").read_text(encoding="utf-8"))
    assert baseline == {"baseline_tag": "baseline-v1", "rendered_from": "0.42.8"}
    template_call = next(c for c in calls if c[:2] == ["helm", "template"])
    assert "0.42.8" in template_call
    assert template_call[-1].endswith("deploy/upstream/otel-demo/values.yaml")
