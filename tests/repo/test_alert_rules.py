"""Verifies WKL-030, WKL-031, WKL-032, WKL-004 (W1-T13): metric map, PrometheusRule, AlertmanagerConfig."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

# `helm_dependencies` is an autouse module fixture that builds the chart dependencies once.
from test_observability_values import helm_dependencies, of_kind, tmpl  # noqa: F401

from scripts.baseline_gate import NOT_SERVER_SIDE, SERVER_SIDE_SERVICES
from scripts.proc import run
from scripts.promql import METRIC_KEYS, load_metric_map
from scripts.workload_transforms import KEPT_COMPONENTS

REPO = Path(__file__).resolve().parents[2]
CHART = REPO / "deploy/charts/observability"

# WKL-031 table: alert -> (for, severity).
WKL_031 = {
    "ServiceHighErrorRate": ("1m", "critical"),
    "ServiceHighLatency": ("2m", "warning"),
    "PodCrashLooping": ("0m", "critical"),
    "PodNotReady": ("2m", "warning"),
    "DeploymentReplicasUnavailable": ("2m", "critical"),
    "ContainerWaiting": ("1m", "critical"),
    "PodUnschedulable": ("1m", "critical"),
    "ContainerOOMKilled": ("0m", "critical"),
    "KafkaConsumerLagHigh": ("2m", "warning"),
    "HighCPU": ("2m", "warning"),
    "HighMemory": ("2m", "warning"),
}
KUBE_STATE_ALERTS = {
    "PodNotReady",
    "DeploymentReplicasUnavailable",
    "ContainerWaiting",
    "PodUnschedulable",
    "ContainerOOMKilled",
}
SERVER_SERVICES = [c for c in KEPT_COMPONENTS if c not in NOT_SERVER_SIDE]
# 13 ServiceHighErrorRate + 13 ServiceHighLatency + 19 PodCrashLooping + 5 kube-state rules
# + 1 KafkaConsumerLagHigh + 19 HighCPU + 19 HighMemory.
EXPECTED_RULE_COUNT = 13 + 13 + 19 + 5 + 1 + 19 + 19


def rules() -> list[dict[str, Any]]:
    rule = next(d for d in tmpl("observability", "local") if d["kind"] == "PrometheusRule")
    assert [g["name"] for g in rule["spec"]["groups"]] == ["rootline-workload"]
    out: list[dict[str, Any]] = rule["spec"]["groups"][0]["rules"]
    return out


def named(alert: str) -> list[dict[str, Any]]:
    return [r for r in rules() if r["alert"] == alert]


def test_metric_map_has_every_wkl_030_key_once() -> None:
    """WKL-030: metric-map.yaml holds exactly the ten metric keys, each with the documented schema."""
    text = (CHART / "files/metric-map.yaml").read_text(encoding="utf-8")
    metrics = load_metric_map()
    assert list(metrics) == list(METRIC_KEYS)
    for key in METRIC_KEYS:
        assert text.count(f"\n  {key}:\n") == 1
    for key, entry in metrics.items():
        assert set(entry) == {"unit", "promql", "jvm_only", "services"}, key
        assert isinstance(entry["promql"], str) and "\n" not in entry["promql"].strip(), key
        assert entry["services"] is None or isinstance(entry["services"], list), key
    assert metrics["gc_pause"]["services"] == ["ad", "fraud-detection"]
    assert metrics["gc_pause"]["jvm_only"] is True
    assert metrics["kafka_consumer_lag"]["services"] == ["fraud-detection"]
    for key in ("request_rate", "error_ratio", "latency_p50", "latency_p95", "latency_p99"):
        assert "$svc" in metrics[key]["promql"]
    for key in ("cpu_usage", "memory_working_set", "restarts"):
        assert "$wl-[a-z0-9]+-[a-z0-9]+" in metrics[key]["promql"]


def test_alert_lists_match_kept_components() -> None:
    """WKL-004, WKL-002: values.yaml service lists equal the kept components minus the non-server ones."""
    values = yaml.safe_load((CHART / "values.yaml").read_text(encoding="utf-8"))["rootlineAlerts"]
    assert values["serverServices"] == list(SERVER_SIDE_SERVICES)
    assert sorted(values["serverServices"]) == sorted(SERVER_SERVICES)
    assert len(values["serverServices"]) == 13
    assert sorted(values["workloads"]) == sorted(KEPT_COMPONENTS)
    assert values["kafkaLagService"] == "fraud-detection"


def test_service_high_error_rate_per_server_side_service() -> None:
    """WKL-031: one ServiceHighErrorRate per kept server-side service, for 1m, critical."""
    found = named("ServiceHighErrorRate")
    assert sorted(r["labels"]["service"] for r in found) == sorted(SERVER_SERVICES)
    for r in found:
        assert r["for"] == "1m"
        assert r["labels"]["severity"] == "critical"
        assert r["labels"]["rootline"] == "true"
        assert r["labels"]["namespace"] == "shop"
        assert "> 0.05" in r["expr"] and "> 0.1" in r["expr"]
        assert f'service="{r["labels"]["service"]}"' in r["expr"]
        assert r["annotations"]["summary"]


def test_pod_crash_looping_has_no_pending_period() -> None:
    """WKL-031: PodCrashLooping fires immediately (`for: 0m`) on 2 or more restarts in 5 minutes."""
    found = named("PodCrashLooping")
    assert sorted(r["labels"]["service"] for r in found) == sorted(KEPT_COMPONENTS)
    for r in found:
        assert r["for"] == "0m"
        assert r["labels"]["severity"] == "critical"
        assert r["expr"].endswith(") >= 2") and "[5m]" in r["expr"]


def test_every_alert_follows_the_wkl_031_table() -> None:
    """WKL-031: `for`, severity and the common labels of every rule; total rule count."""
    all_rules = rules()
    assert {r["alert"] for r in all_rules} == set(WKL_031)
    for r in all_rules:
        want_for, want_severity = WKL_031[r["alert"]]
        assert r["for"] == want_for, r["alert"]
        assert r["labels"]["severity"] == want_severity, r["alert"]
        assert r["labels"]["rootline"] == "true"
        assert r["labels"]["namespace"] == "shop"
        assert r["annotations"]["summary"]
        if r["alert"] in KUBE_STATE_ALERTS:
            assert "service" not in r["labels"]
            assert "label_replace(" in r["expr"] and '"service", "$1"' in r["expr"]
        else:
            assert r["labels"]["service"] in KEPT_COMPONENTS
    assert len(all_rules) == EXPECTED_RULE_COUNT, f"rendered {len(all_rules)} rules"


def test_wkl_031_expressions() -> None:
    """WKL-031: the expression text of the kube-state-metrics, lag, CPU and memory rules."""
    assert 'kube_pod_status_ready{namespace="shop",condition="false"}' in named("PodNotReady")[0]["expr"]
    assert (
        'kube_deployment_status_replicas_unavailable{namespace="shop"} > 0'
        in named("DeploymentReplicasUnavailable")[0]["expr"]
    )
    waiting = named("ContainerWaiting")[0]["expr"]
    assert 'reason=~"ImagePullBackOff|ErrImagePull|CrashLoopBackOff|CreateContainerConfigError"' in waiting
    assert 'kube_pod_status_unschedulable{namespace="shop"} > 0' in named("PodUnschedulable")[0]["expr"]
    oom = named("ContainerOOMKilled")[0]["expr"]
    assert 'reason="OOMKilled"} == 1' in oom and "and on(pod)" in oom and "> 0" in oom
    lag = named("KafkaConsumerLagHigh")
    assert [r["labels"]["service"] for r in lag] == ["fraud-detection"]
    assert 'kafka_consumer_records_lag{service_name="fraud-detection"' in lag[0]["expr"]
    for r in named("HighCPU"):
        assert 'resource="cpu"' in r["expr"] and r["expr"].endswith("> 0.9")
    for r in named("HighMemory"):
        assert 'resource="memory"' in r["expr"] and r["expr"].endswith("> 0.9")


def test_thresholds_are_used_in_expressions() -> None:
    """WKL-031: ServiceHighLatency and KafkaConsumerLagHigh use the committed alert-thresholds.yaml values."""
    thresholds = yaml.safe_load((CHART / "files/alert-thresholds.yaml").read_text(encoding="utf-8"))
    for r in named("ServiceHighLatency"):
        svc = r["labels"]["service"]
        assert r["expr"].endswith(f") > {thresholds['ServiceHighLatency'][svc]:g}"), svc
        assert "histogram_quantile(0.95" in r["expr"]
    lag = named("KafkaConsumerLagHigh")[0]["expr"]
    assert lag.endswith(f") > {thresholds['KafkaConsumerLagHigh']['fraud-detection']:g}")


def test_alertmanager_config() -> None:
    """WKL-032: one route and one receiver `rootline-api`, authorization from Secret alertmanager-webhook."""
    docs = tmpl("observability", "local")
    cfg = of_kind(docs, "AlertmanagerConfig")
    assert len(cfg) == 1 and cfg[0]["metadata"]["namespace"] == "observability"
    spec = cfg[0]["spec"]
    assert spec["route"] == {
        "receiver": "rootline-api",
        "groupBy": ["alertname", "service"],
        "groupWait": "30s",
        "groupInterval": "2m",
        "repeatInterval": "1h",
    }
    assert [r["name"] for r in spec["receivers"]] == ["rootline-api"]
    hooks = spec["receivers"][0]["webhookConfigs"]
    assert hooks == [
        {
            "url": "http://api.rootline.svc.cluster.local/hooks/alertmanager",
            "sendResolved": True,
            "httpConfig": {
                "authorization": {
                    "type": "Bearer",
                    "credentials": {"name": "alertmanager-webhook", "key": "token"},
                }
            },
        }
    ]
    alertmanager = next(d for d in docs if d["kind"] == "Alertmanager")
    assert alertmanager["spec"]["alertmanagerConfigMatcherStrategy"] == {"type": "None"}


def test_alertmanager_webhook_secret_is_generated() -> None:
    """WKL-032, SEC-100: ExternalSecret alertmanager-webhook generates `token` from the Password generator."""
    es = next(d for d in of_kind(tmpl("observability", "local"), "ExternalSecret"))
    assert es["metadata"] == {"name": "alertmanager-webhook", "namespace": "observability"}
    assert es["spec"]["refreshInterval"] == "0"
    ref = es["spec"]["dataFrom"][0]["sourceRef"]["generatorRef"]
    assert (ref["kind"], ref["name"]) == ("Password", "password-48")
    assert es["spec"]["target"]["name"] == "alertmanager-webhook"
    assert es["spec"]["target"]["template"]["data"] == {"token": "{{ .password }}"}


@pytest.mark.skipif(shutil.which("promtool") is None, reason="promtool is not on PATH")
def test_promtool_accepts_the_rules(tmp_path: Path) -> None:
    """WKL-031: `promtool check rules` accepts the rendered rule group."""
    rule = next(d for d in tmpl("observability", "local") if d["kind"] == "PrometheusRule")
    target = tmp_path / "rules.yaml"
    target.write_text(yaml.safe_dump(rule["spec"], width=100000), encoding="utf-8")
    result = run(["promtool", "check", "rules", str(target)], check=False)
    assert result.returncode == 0, result.stdout + result.stderr
