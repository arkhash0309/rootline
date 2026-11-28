"""Verifies WKL-010, WKL-011 (TST-WKL-001), PG-11, PG-12, PG-25, PG-29."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import scripts.render_workload as render_workload
from scripts.workload_transforms import (
    COLLECTOR_FQDN,
    KEPT_COMPONENTS,
    UnresolvedReferenceError,
    dump,
    transform,
)

FIX = Path(__file__).parent / "fixtures/otel-demo-mini.yaml"


def docs() -> list[dict[str, Any]]:
    return [d for d in yaml.safe_load_all(FIX.read_text(encoding="utf-8")) if d]


def test_tst_wkl_001_deterministic() -> None:
    """TST-WKL-001: two renders are byte-identical."""
    a = {k: dump(v) for k, v in transform(docs()).items()}
    b = {k: dump(v) for k, v in transform(docs()).items()}
    assert a == b


def test_namespace_and_no_secrets() -> None:
    out = transform(docs())
    objs = [o for v in out.values() for o in v]
    assert all(o["metadata"]["namespace"] == "shop" for o in objs)
    assert not any(o["kind"] == "Secret" for o in objs)


def test_labels_on_workloads() -> None:
    dep = next(o for o in transform(docs())["payment"] if o["kind"] == "Deployment")
    assert dep["metadata"]["labels"]["app.kubernetes.io/part-of"] == "rootline-workload"
    assert dep["spec"]["template"]["metadata"]["labels"]["rootline.dev/workload"] == "payment"


def test_readiness_probe_added() -> None:
    dep = next(o for o in transform(docs())["payment"] if o["kind"] == "Deployment")
    probe = dep["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
    assert probe == {
        "tcpSocket": {"port": 8080},
        "initialDelaySeconds": 5,
        "periodSeconds": 10,
        "failureThreshold": 3,
    }


def test_collector_name_rewritten_ports_kept() -> None:
    dep = next(o for o in transform(docs())["payment"] if o["kind"] == "Deployment")
    env = {e["name"]: e.get("value") for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["OTEL_COLLECTOR_NAME"] == COLLECTOR_FQDN
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://$(OTEL_COLLECTOR_NAME):4317"


def test_flagd_mounts_configmap_directly() -> None:
    out = transform(docs())
    dep = next(o for o in out["flagd"] if o["kind"] == "Deployment")
    spec = dep["spec"]["template"]["spec"]
    assert [c["name"] for c in spec.get("initContainers", [])] == []
    assert [c["name"] for c in spec["containers"]] == ["flagd"]
    vols = {v["name"]: v for v in spec["volumes"]}
    assert vols["config-rw"] == {"name": "config-rw", "configMap": {"name": "flagd-config"}}
    assert "config-ro" not in vols


def test_flags_all_off() -> None:
    cm = transform(docs())["flagd-config"][0]
    flags = json.loads(cm["data"]["demo.flagd.json"])["flags"]
    assert {f["defaultVariant"] for f in flags.values()} == {"off"}


def test_load_generator_env() -> None:
    dep = next(o for o in transform(docs())["load-generator"] if o["kind"] == "Deployment")
    env = {e["name"]: e.get("value") for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert (env["LOCUST_USERS"], env["LOCUST_SPAWN_RATE"], env["LOCUST_AUTOSTART"]) == ("10", "2", "true")


def test_networkpolicies_file() -> None:
    names = [o["metadata"]["name"] for o in transform(docs())["networkpolicies"]]
    assert names == ["allow-observability-scrape", "allow-same-namespace"]


def test_kafka_controller_quorum_voter_is_localhost() -> None:
    """WKL-010 step 7, PG-29 (ADR 0048): the KRaft voter is the kafka pod itself, not Service kafka."""
    out = transform(docs())
    assert [o["kind"] for o in out["kafka"]] == ["Service", "Deployment"]
    dep = next(o for o in out["kafka"] if o["kind"] == "Deployment")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    names = [e["name"] for e in container["env"]]
    env = {e["name"]: e.get("value") for e in container["env"]}
    assert names.count("KAFKA_CONTROLLER_QUORUM_VOTERS") == 1
    assert env["KAFKA_CONTROLLER_QUORUM_VOTERS"] == "1@localhost:9093"
    assert env["KAFKA_LISTENERS"] == "PLAINTEXT://:9092,CONTROLLER://:9093"
    assert env["KAFKA_ADVERTISED_LISTENERS"] == "PLAINTEXT://kafka:9092"
    assert container["readinessProbe"] == {
        "tcpSocket": {"port": 9092},
        "initialDelaySeconds": 5,
        "periodSeconds": 10,
        "failureThreshold": 3,
    }
    svc = next(o for o in out["kafka"] if o["kind"] == "Service")
    assert "publishNotReadyAddresses" not in svc["spec"]


def test_kafka_controller_quorum_voter_added_when_absent() -> None:
    """WKL-010 step 7, PG-29 (ADR 0048): a chart output without the variable gets it appended."""
    ds = docs()
    dep = next(d for d in ds if d["kind"] == "Deployment" and d["metadata"]["name"] == "kafka")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    container["env"] = [e for e in container["env"] if e["name"] != "KAFKA_CONTROLLER_QUORUM_VOTERS"]
    out = next(o for o in transform(ds)["kafka"] if o["kind"] == "Deployment")
    env = out["spec"]["template"]["spec"]["containers"][0]["env"]
    assert env[-1] == {"name": "KAFKA_CONTROLLER_QUORUM_VOTERS", "value": "1@localhost:9093"}


def where(out: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str], str]:
    """(kind, name) -> file stem, for every object in the output."""
    return {(o["kind"], o["metadata"]["name"]): stem for stem, objs in out.items() for o in objs}


def test_referenced_serviceaccount_kept() -> None:
    """PG-25 D1, D2: ServiceAccount shop has no component label and is shared -> serviceaccount."""
    out = transform(docs())
    assert where(out)[("ServiceAccount", "shop")] == "serviceaccount"
    assert [(o["kind"], o["metadata"]["name"]) for o in out["serviceaccount"]] == [("ServiceAccount", "shop")]
    assert out["serviceaccount"][0]["metadata"]["namespace"] == "shop"


def test_referenced_configmap_kept_in_workload_file() -> None:
    """PG-25 D1, D2: one referrer -> the workload's file; several -> configmaps."""
    out = transform(docs())
    assert where(out)[("ConfigMap", "postgresql-init")] == "astronomy-db"
    assert [o["kind"] for o in out["astronomy-db"]] == ["ConfigMap", "Deployment"]
    assert where(out)[("ConfigMap", "shop-shared-env")] == "configmaps"
    assert where(out)[("ConfigMap", "flagd-config")] == "flagd-config"


def test_unreferenced_unlabelled_object_dropped() -> None:
    """PG-25 D1: no kept component and no reference from a kept workload -> dropped."""
    found = where(transform(docs()))
    assert ("ConfigMap", "orphan-config") not in found
    assert ("ConfigMap", "jaeger-sampling") not in found  # referenced only by the dropped jaeger Deployment
    assert ("Deployment", "jaeger") not in found


def test_every_reference_of_kept_workload_resolves() -> None:
    """PG-25 D4: every serviceAccountName and ConfigMap reference of every kept workload is in the output."""
    out = transform(docs())
    found = set(where(out))
    wanted: set[tuple[str, str]] = set()
    for o in (o for objs in out.values() for o in objs if o["kind"] in ("Deployment", "StatefulSet")):
        spec = o["spec"]["template"]["spec"]
        if spec.get("serviceAccountName"):
            wanted.add(("ServiceAccount", spec["serviceAccountName"]))
        for v in spec.get("volumes") or []:
            if "configMap" in v:
                wanted.add(("ConfigMap", v["configMap"]["name"]))
        for c in (spec.get("containers") or []) + (spec.get("initContainers") or []):
            for src in c.get("envFrom") or []:
                if "configMapRef" in src:
                    wanted.add(("ConfigMap", src["configMapRef"]["name"]))
            for e in c.get("env") or []:
                if "configMapKeyRef" in (e.get("valueFrom") or {}):
                    wanted.add(("ConfigMap", e["valueFrom"]["configMapKeyRef"]["name"]))
    assert wanted == {
        ("ServiceAccount", "shop"),
        ("ConfigMap", "flagd-config"),
        ("ConfigMap", "postgresql-init"),
        ("ConfigMap", "shop-shared-env"),
    }
    assert wanted <= found


def test_missing_reference_rejected() -> None:
    """PG-25 D3: a required reference that the chart output lacks raises, naming every referrer."""
    ds = [d for d in docs() if (d["kind"], d["metadata"]["name"]) != ("ConfigMap", "postgresql-init")]
    with pytest.raises(UnresolvedReferenceError) as err:
        transform(ds)
    assert err.value.errors == [
        "unresolved reference Deployment/astronomy-db -> ConfigMap/postgresql-init "
        "(not in the helm template output)"
    ]


def test_secret_reference_rejected() -> None:
    """PG-25 D3: Secrets are never kept, so a required Secret reference of a kept workload is an error."""
    ds = docs()
    dep = next(d for d in ds if d["kind"] == "Deployment" and d["metadata"]["name"] == "payment")
    dep["spec"]["template"]["spec"]["containers"][0]["envFrom"].append(
        {"secretRef": {"name": "shop-registry-credentials"}}
    )
    with pytest.raises(UnresolvedReferenceError) as err:
        transform(ds)
    assert err.value.errors == [
        "unresolved reference Deployment/payment -> Secret/shop-registry-credentials "
        "(Secrets are removed by WKL-010 step 2)"
    ]


def test_transform_does_not_mutate_input() -> None:
    """WKL-011: transform is a pure function of its input."""
    original = docs()
    snapshot = copy.deepcopy(original)
    transform(original)
    assert original == snapshot


def test_only_kept_components_remain() -> None:
    """WKL-002: objects of components outside the kept list are dropped."""
    out = transform(docs())
    assert "jaeger" not in out
    reserved = {"flagd-config", "networkpolicies", "serviceaccount", "configmaps"}
    assert set(out) - reserved <= set(KEPT_COMPONENTS)
    assert len(KEPT_COMPONENTS) == 19


def test_component_files_sorted_by_kind_then_name() -> None:
    """WKL-010 step 8."""
    kinds = [o["kind"] for o in transform(docs())["payment"]]
    assert kinds == ["Service", "Deployment"]


def test_existing_readiness_probe_is_kept() -> None:
    """WKL-010 step 4: a container that already has a readinessProbe keeps it."""
    source = docs()
    dep = next(d for d in source if d["kind"] == "Deployment" and d["metadata"]["name"] == "payment")
    existing = {"httpGet": {"path": "/healthz", "port": 8080}}
    dep["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = existing
    out = next(o for o in transform(source)["payment"] if o["kind"] == "Deployment")
    assert out["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] == existing


def test_endpoint_without_collector_name_gets_fqdn_and_keeps_port() -> None:
    """PG-12: an endpoint without $(OTEL_COLLECTOR_NAME) gets the FQDN host, same scheme and port."""
    dep = next(o for o in transform(docs())["load-generator"] if o["kind"] == "Deployment")
    env = {e["name"]: e.get("value") for e in dep["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == f"http://{COLLECTOR_FQDN}:4318"


def test_optional_missing_reference_is_ignored() -> None:
    """PG-25 D3: an optional reference to an absent object is not an error and writes nothing."""
    ds = [d for d in docs() if (d["kind"], d["metadata"]["name"]) != ("ConfigMap", "shop-shared-env")]
    for d in ds:
        if d["kind"] == "Deployment" and d["metadata"]["name"] == "payment":
            d["spec"]["template"]["spec"]["containers"][0]["envFrom"][0]["configMapRef"]["optional"] = True
        if d["kind"] == "Deployment" and d["metadata"]["name"] == "load-generator":
            env = d["spec"]["template"]["spec"]["containers"][0]["env"]
            next(e for e in env if e["name"] == "SHOP_REGION")["valueFrom"]["configMapKeyRef"]["optional"] = (
                True
            )
    out = transform(ds)
    assert "configmaps" not in out


def test_dump_is_sorted_yaml_stream() -> None:
    """WKL-010 step 8: keys sorted, documents separated by a --- line."""
    text = dump(transform(docs())["networkpolicies"])
    loaded = [d for d in yaml.safe_load_all(text) if d]
    assert [d["kind"] for d in loaded] == ["NetworkPolicy", "NetworkPolicy"]
    assert text.index("apiVersion:") < text.index("kind:") < text.index("metadata:")


class _Result:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def _fake_run(calls: list[list[str]], stdout: str) -> Any:
    def fake_run(cmd: list[str], **_: Any) -> _Result:
        calls.append(cmd)
        return _Result(stdout)

    return fake_run


def test_render_workload_writes_files_and_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-001, WKL-011: one file per stem, stale files removed, baseline.json written."""
    calls: list[list[str]] = []
    monkeypatch.setattr(render_workload, "run", _fake_run(calls, FIX.read_text(encoding="utf-8")))
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
        "astronomy-db.yaml",
        "configmaps.yaml",
        "flagd-config.yaml",
        "flagd.yaml",
        "kafka.yaml",
        "load-generator.yaml",
        "networkpolicies.yaml",
        "payment.yaml",
        "serviceaccount.yaml",
    ]
    baseline = json.loads((out.parent / ".rootline/baseline.json").read_text(encoding="utf-8"))
    assert baseline == {"baseline_tag": "baseline-v2", "rendered_from": "0.42.8"}
    template_call = next(c for c in calls if c[:2] == ["helm", "template"])
    assert "0.42.8" in template_call
    assert template_call[-1].endswith("deploy/upstream/otel-demo/values.yaml")


def test_render_workload_exit_3_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """PG-25 D3: unresolved reference -> stderr lines, exit 3, output directory not created."""
    text = "---\n".join(
        yaml.safe_dump(d)
        for d in docs()
        if (d["kind"], d["metadata"]["name"]) != ("ConfigMap", "postgresql-init")
    )
    monkeypatch.setattr(render_workload, "run", _fake_run([], text))
    out = tmp_path / "env/workload"
    monkeypatch.setattr("sys.argv", ["render_workload.py", "--out", str(out)])

    assert render_workload.main() == 3
    assert capsys.readouterr().err == (
        "render_workload: unresolved reference Deployment/astronomy-db -> ConfigMap/postgresql-init "
        "(not in the helm template output)\n"
    )
    assert not out.exists()
    assert not (out.parent / ".rootline").exists()
