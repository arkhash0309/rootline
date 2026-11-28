"""Verifies WKL-004 (baseline health gate pass criteria) and WKL-030 (metric-map use) for W1-T13."""

from __future__ import annotations

from typing import Any

from scripts import baseline_gate
from scripts.baseline_gate import Row, collect_samples, evaluate, format_table
from scripts.promql import load_metric_map


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
