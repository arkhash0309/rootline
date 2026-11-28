"""Verifies WKL-004 (baseline health gate pass criteria) and WKL-030 (metric-map use) for W1-T13."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import baseline_gate
from scripts.baseline_gate import Row, collect_samples, evaluate, format_table
from scripts.promql import PromError, load_metric_map


class FakeProm:
    """Answers `scalar` from a table keyed by a substring of the expression."""

    def __init__(self, error_ratio: dict[str, float | None], restarts: dict[str, float | None]) -> None:
        self.error_ratio = error_ratio
        self.restarts = restarts

    def scalar(self, expr: str, ts: float | None = None) -> float | None:
        table = self.restarts if expr.startswith("sum(increase(") else self.error_ratio
        for svc, value in table.items():
            if f'"{svc}"' in expr or f'pod=~"{svc}-' in expr:
                return value
        return 0.0

    def query(self, expr: str, ts: float | None = None) -> list[dict[str, Any]]:
        return []

    def query_range(self, expr: str, start: float, end: float, step_s: float) -> list[dict[str, Any]]:
        value = "NaN" if 'service="fraud-detection"' in expr else "0.25"
        return [{"metric": {}, "values": [[start, value], [start + step_s, "0.5"]]}]


def test_server_side_services_are_the_thirteen_kept_components() -> None:
    """WKL-004: kept components minus the six non-server components leave 13 services."""
    assert len(baseline_gate.SERVER_SIDE_SERVICES) == 13
    for name in baseline_gate.NOT_SERVER_SIDE:
        assert name not in baseline_gate.SERVER_SIDE_SERVICES
    assert "fraud-detection" in baseline_gate.SERVER_SIDE_SERVICES


def test_pass_criteria() -> None:
    """WKL-004: PASS needs error_ratio <= 0.01, zero restarts and data for both values."""
    assert Row("a", 0.01, 0.0).passed
    assert not Row("a", 0.0101, 0.0).passed
    assert not Row("a", 0.0, 1.0).passed
    assert not Row("a", None, 0.0).passed
    assert not Row("a", 0.0, None).passed


def test_evaluate_and_table() -> None:
    """WKL-004: one row per server-side service; the table shows PASS and FAIL and `no data`."""
    prom = FakeProm({"payment": 0.02, "cart": None}, {"checkout": 2.0})
    rows = evaluate(prom, load_metric_map(), 30, 1000.0)
    assert [r.service for r in rows] == list(baseline_gate.SERVER_SIDE_SERVICES)
    by_name = {r.service: r for r in rows}
    assert by_name["payment"].error_ratio == 0.02 and not by_name["payment"].passed
    assert by_name["checkout"].restarts == 2.0 and not by_name["checkout"].passed
    assert by_name["cart"].error_ratio is None and not by_name["cart"].passed
    assert by_name["frontend"].passed
    table = format_table(rows)
    assert table.splitlines()[0].split("|")[0].strip() == "service"
    assert "no data" in table and "FAIL" in table and "PASS" in table


def test_expressions_use_the_metric_map_and_the_pod_regex() -> None:
    """WKL-004, WKL-030: the gate averages the metric-map error_ratio over the window."""
    expr = baseline_gate.error_ratio_expr(load_metric_map(), "payment", 30)
    assert expr.startswith("avg_over_time((") and expr.endswith(")[30m:15s])")
    assert 'service="payment"' in expr and "$svc" not in expr
    assert baseline_gate.restarts_expr("frontend", 30) == (
        'sum(increase(kube_pod_container_status_restarts_total{namespace="shop",'
        'pod=~"frontend-[a-z0-9]+-[a-z0-9]+"}[30m]))'
    )


def test_samples_cover_latency_of_every_service_and_the_lag() -> None:
    """WKL-031: samples.json holds latency_p95 per server-side service and the lag; NaN is dropped."""
    samples = collect_samples(FakeProm({}, {}), load_metric_map(), 0.0, 60.0)
    assert set(samples) == {f"latency_p95:{s}" for s in baseline_gate.SERVER_SIDE_SERVICES} | {
        "kafka_consumer_lag:fraud-detection"
    }
    assert samples["latency_p95:payment"] == [0.25, 0.5]
    assert samples["latency_p95:fraud-detection"] == [0.5]


# --- B1: precondition failures exit 2 and never raise (WKL-004) ---------------------------------------------

FLAGS_OFF = json.dumps({"flags": {"a": {"defaultVariant": "off"}, "b": {"defaultVariant": "off"}}})
FLAGS_ONE_ON = json.dumps({"flags": {"a": {"defaultVariant": "off"}, "adFailure": {"defaultVariant": "on"}}})


def _cm(text: str) -> str:
    return json.dumps({"data": {"demo.flagd.json": text}})


def _dep(env: list[dict[str, str]] | None, users: str = "10") -> str:
    container: dict[str, Any] = {"name": "load-generator"}
    if env is not None:
        container["env"] = env or [{"name": "LOCUST_USERS", "value": users}]
    return json.dumps({"spec": {"template": {"spec": {"containers": [container]}}}})


def _fake_run(cm_out: str, dep_out: str, returncode: int = 0) -> Any:
    def fake(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        out = cm_out if "configmap" in cmd else dep_out
        return subprocess.CompletedProcess(cmd, returncode, stdout=out, stderr="boom")

    return fake


def test_preconditions_pass_when_flags_off_and_load_normal(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004: all flags off and LOCUST_USERS=10 give no problem."""
    monkeypatch.setattr(baseline_gate, "run", _fake_run(_cm(FLAGS_OFF), _dep([])))
    assert baseline_gate.check_preconditions("ctx") == []


def test_missing_kubectl_is_a_problem_not_a_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004: a missing kubectl binary yields problems (exit 2), not FileNotFoundError (exit 1)."""

    def boom(cmd: list[str], **_: Any) -> None:
        raise FileNotFoundError("kubectl")

    monkeypatch.setattr(baseline_gate, "run", boom)
    problems = baseline_gate.check_preconditions("ctx")
    assert len(problems) == 2 and all("kubectl is not installed" in p for p in problems)
    assert baseline_gate.main(["--minutes", "1"]) == 2


def test_kubectl_timeout_is_a_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004: a kubectl timeout yields a problem."""

    def slow(cmd: list[str], **_: Any) -> None:
        raise subprocess.TimeoutExpired(cmd, 600)

    monkeypatch.setattr(baseline_gate, "run", slow)
    assert any("timed out" in p for p in baseline_gate.check_preconditions("ctx"))


def test_kubectl_failure_is_a_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004: a non-zero kubectl exit yields a problem with the stderr text."""
    monkeypatch.setattr(baseline_gate, "run", _fake_run("", "", returncode=1))
    problems = baseline_gate.check_preconditions("ctx")
    assert len(problems) == 2 and "boom" in problems[0]


def test_flag_not_off_is_a_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004: a flag whose defaultVariant is not off is named in the problem."""
    monkeypatch.setattr(baseline_gate, "run", _fake_run(_cm(FLAGS_ONE_ON), _dep([])))
    problems = baseline_gate.check_preconditions("ctx")
    assert len(problems) == 1 and "adFailure" in problems[0]
    assert baseline_gate.main(["--minutes", "1"]) == 2


def test_locust_users_not_ten_is_a_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004, WKL-040: LOCUST_USERS other than 10 is a problem."""
    dep = json.dumps(
        {"spec": {"template": {"spec": {"containers": [{"env": [{"name": "LOCUST_USERS", "value": "50"}]}]}}}}
    )
    monkeypatch.setattr(baseline_gate, "run", _fake_run(_cm(FLAGS_OFF), dep))
    problems = baseline_gate.check_preconditions("ctx")
    assert problems == ["LOCUST_USERS is '50', expected '10'"]


@pytest.mark.parametrize(
    ("cm_out", "dep_out", "fragment"),
    [
        ("not json", _dep([]), "is not JSON"),
        (_cm("{broken"), _dep([]), "ConfigMap shop/flagd-config is malformed"),
        (json.dumps({"metadata": {}}), _dep([]), "ConfigMap shop/flagd-config is malformed"),
        (_cm(FLAGS_OFF), "[1, 2", "is not JSON"),
        (_cm(FLAGS_OFF), _dep(None), "no readable container env"),
        (_cm(FLAGS_OFF), json.dumps({"spec": {"template": {"spec": {"containers": []}}}}), "no readable"),
    ],
)
def test_malformed_kubectl_output_is_a_problem(
    monkeypatch: pytest.MonkeyPatch, cm_out: str, dep_out: str, fragment: str
) -> None:
    """WKL-004: malformed JSON, a ConfigMap without data and a container without env yield problems."""
    monkeypatch.setattr(baseline_gate, "run", _fake_run(cm_out, dep_out))
    problems = baseline_gate.check_preconditions("ctx")
    assert problems and any(fragment in p for p in problems)


def test_port_forward_start_failure_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-004: a Popen OSError when the port-forward starts exits 2."""

    def popen(*_: Any, **__: Any) -> None:
        raise FileNotFoundError("kubectl")

    monkeypatch.setattr(subprocess, "Popen", popen)
    assert baseline_gate.main(["--minutes", "1", "--skip-preconditions"]) == 2


# --- N1: main() with a fake Prometheus client ---------------------------------------------------------------


class Clock:
    """Fake clock: `sleep` advances `time`; replaces the `time` module inside `scripts.baseline_gate`."""

    def __init__(self) -> None:
        self.now = 1_000_000.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class ScriptedClient:
    """Stands in for `PromClient`; behaviour set through class attributes by each test."""

    error_ratio = 0.0
    restarts: float | None = 0.0
    fail_polls = False
    fail_always = False
    fail_final_scalar = False
    calls = 0
    clock = Clock()

    def __init__(self, base_url: str, timeout_s: float = 30.0) -> None:
        self.base_url = base_url

    def query(self, expr: str, ts: float | None = None) -> list[dict[str, Any]]:
        type(self).calls += 1
        if type(self).fail_always or (type(self).fail_polls and type(self).calls > 1):
            raise PromError("down")
        if "> 0" in expr:
            return [{"metric": {"pod": "cart-abc-def"}, "value": [0, "1"]}]
        return []

    def query_range(self, expr: str, start: float, end: float, step_s: float) -> list[dict[str, Any]]:
        return [{"metric": {}, "values": [[start, "0.1"]]}]

    def scalar(self, expr: str, ts: float | None = None) -> float | None:
        if type(self).fail_final_scalar and ts is not None:
            # only the final evaluation passes an evaluation time; the progress lines do not
            raise PromError("down at the end of the run")
        if expr.startswith("sum(increase("):
            return type(self).restarts
        return type(self).error_ratio


@pytest.fixture
def scripted(monkeypatch: pytest.MonkeyPatch) -> type[ScriptedClient]:
    ScriptedClient.error_ratio = 0.0
    ScriptedClient.restarts = 0.0
    ScriptedClient.fail_polls = False
    ScriptedClient.fail_always = False
    ScriptedClient.fail_final_scalar = False
    ScriptedClient.calls = 0
    clock = ScriptedClient.clock = Clock()
    monkeypatch.setattr(baseline_gate, "PromClient", ScriptedClient)
    monkeypatch.setattr(baseline_gate, "time", SimpleNamespace(time=clock.time, sleep=clock.sleep))
    return ScriptedClient


def _gate(tmp_path: Path) -> int:
    """Run `main` with the fake clock of the `scripted` fixture (no real sleeping)."""
    args = ["--minutes", "2", "--poll-s", "60", "--prometheus-url", "http://prom", "--skip-preconditions"]
    args += ["--date", "2026-11-28", "--out-dir", str(tmp_path)]
    return baseline_gate.main(args, sleep=ScriptedClient.clock.sleep)


def test_main_pass_writes_samples_and_report(
    scripted: type[ScriptedClient], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """WKL-004: all rows PASS exits 0 and writes samples.json and report.json."""
    assert _gate(tmp_path) == 0
    out = capsys.readouterr().out
    assert "baseline_gate: PASS" in out and "[  1.0/2 min]" in out
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert len(report["rows"]) == 13 and all(r["pass"] for r in report["rows"])
    assert report["failed_polls"] == 0
    samples = json.loads((tmp_path / "samples.json").read_text(encoding="utf-8"))
    assert samples["step_s"] == 15 and "kafka_consumer_lag:fraud-detection" in samples["samples"]


def test_main_fail_on_restarts_exits_1(scripted: type[ScriptedClient], tmp_path: Path) -> None:
    """WKL-004: a restart in the window makes every row FAIL and the exit status 1."""
    scripted.restarts = 1.0
    assert _gate(tmp_path) == 1
    assert not any(r["pass"] for r in json.loads((tmp_path / "report.json").read_text())["rows"])


def test_main_no_data_is_fail(scripted: type[ScriptedClient], tmp_path: Path) -> None:
    """WKL-004: a restarts value without data is FAIL."""
    scripted.restarts = None
    assert _gate(tmp_path) == 1


def test_main_counts_failed_polls(scripted: type[ScriptedClient], tmp_path: Path) -> None:
    """WKL-004: a failed poll is counted in report.json and does not stop the run."""
    scripted.fail_polls = True
    # the final evaluation uses scalar/query_range, which do not fail; only progress-line queries do
    assert _gate(tmp_path) == 0
    assert json.loads((tmp_path / "report.json").read_text())["failed_polls"] == 2


def test_main_prometheus_unreachable_exits_2(scripted: type[ScriptedClient], tmp_path: Path) -> None:
    """WKL-004: Prometheus unreachable at the start exits 2."""
    scripted.fail_always = True
    assert _gate(tmp_path) == 2


def test_main_prometheus_unreachable_at_the_end_exits_2(
    scripted: type[ScriptedClient], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """WKL-004: Prometheus unreachable during the final evaluation exits 2 and writes no report.json."""
    scripted.fail_final_scalar = True
    assert _gate(tmp_path) == 2
    assert "Prometheus unreachable at the end of the run" in capsys.readouterr().err
    assert not (tmp_path / "report.json").exists()


def test_main_rejects_non_positive_arguments(tmp_path: Path) -> None:
    """WKL-004: --minutes and --poll-s must be >= 1."""
    assert baseline_gate.main(["--minutes", "0", "--skip-preconditions"]) == 2
    assert baseline_gate.main(["--poll-s", "0", "--skip-preconditions"]) == 2


def test_port_forward_url_and_stop() -> None:
    """WKL-004: PortForward exposes a loopback URL and stop() on a never started forward is a no-op."""
    forward = baseline_gate.PortForward("ctx")
    assert forward.url == f"http://127.0.0.1:{forward.port}"
    forward.stop()
