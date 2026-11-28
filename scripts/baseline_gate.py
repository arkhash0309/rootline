"""Baseline health gate of the workload (WKL-004, W1-T13).

Usage:
  uv run python scripts/baseline_gate.py [--minutes 30] [--context k3d-rootline] [--prometheus-url URL]
                                         [--poll-s 60] [--date YYYY-MM-DD] [--out-dir data/baseline/<date>]

What it does (WKL-004: all flags off, load level `normal`, 30 minutes):

1. Precondition check with `kubectl` (exit 2 on failure): ConfigMap `shop/flagd-config` has `defaultVariant:
   "off"` on every flag and Deployment `shop/load-generator` has env `LOCUST_USERS=10`.
2. Unless `--prometheus-url` is given, starts `kubectl -n observability port-forward svc/prometheus-operated
   <free port>:9090` and restarts it whenever it exits during the run.
3. Polls Prometheus every `--poll-s` seconds (default 60 s) for `--minutes` minutes (default 30) and
   prints one progress line per poll: the highest 5 minute `error_ratio` and the pods restarted in the
   window so far. A failed poll is printed and counted; it does not stop the run.
4. At the end, for every kept server-side service (every kept component of
   `scripts.workload_transforms.KEPT_COMPONENTS` except `load-generator`, `frontend-proxy`, `kafka`,
   `valkey-cart`, `astronomy-db` and `flagd`; 13 services) computes
   - `error_ratio`: `avg_over_time((<error_ratio expr of metric-map.yaml>)[<minutes>m:15s])` at the end time;
   - `restarts`: `sum(increase(kube_pod_container_status_restarts_total{namespace="shop",
     pod=~"<svc>-[a-z0-9]+-[a-z0-9]+"}[<minutes>m]))`;
   and prints the table `service | error_ratio | restarts | PASS/FAIL`.
   A row is PASS when `error_ratio <= 0.01`, `restarts == 0` and both values exist (no data is FAIL).
5. Writes `<out-dir>/samples.json` (`{"date", "minutes", "step_s": 15, "samples": {"latency_p95:<svc>": [...],
   "kafka_consumer_lag:fraud-detection": [...]}}`, finite points only; input of
   `scripts/derive_thresholds.py --samples`) and `<out-dir>/report.json` (the table rows).

Exit codes: 0 every row PASS; 1 at least one row FAIL; 2 precondition failed, Prometheus unreachable at the
start or the end, or invalid arguments.
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run
from scripts.promql import PromClient, PromError, load_metric_map, render
from scripts.workload_transforms import KEPT_COMPONENTS

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXT = "k3d-rootline"
DEFAULT_MINUTES = 30
DEFAULT_POLL_S = 60
STEP_S = 15  # WKL-021 scrape interval; range-query step of samples.json
MAX_ERROR_RATIO = 0.01  # WKL-004 pass criterion: error_ratio <= 1 %
# WKL-004: kept components that are not server-side services (no server spans, or not in the request path).
NOT_SERVER_SIDE = ("load-generator", "frontend-proxy", "kafka", "valkey-cart", "astronomy-db", "flagd")
SERVER_SIDE_SERVICES = tuple(c for c in KEPT_COMPONENTS if c not in NOT_SERVER_SIDE)
LAG_SERVICE = "fraud-detection"
EXPECTED_LOCUST_USERS = "10"  # WKL-040 level `normal`


class Prom(Protocol):
    def query(self, expr: str, ts: float | None = None) -> list[dict[str, Any]]: ...

    def query_range(self, expr: str, start: float, end: float, step_s: float) -> list[dict[str, Any]]: ...

    def scalar(self, expr: str, ts: float | None = None) -> float | None: ...


@dataclass(frozen=True)
class Row:
    service: str
    error_ratio: float | None
    restarts: float | None

    @property
    def passed(self) -> bool:
        return (
            self.error_ratio is not None
            and self.restarts is not None
            and self.error_ratio <= MAX_ERROR_RATIO
            and self.restarts == 0
        )


def pod_regex(svc: str) -> str:
    return f"{svc}-[a-z0-9]+-[a-z0-9]+"


def restarts_expr(svc: str, minutes: int) -> str:
    return (
        f'sum(increase(kube_pod_container_status_restarts_total{{namespace="shop",pod=~"{pod_regex(svc)}"}}'
        f"[{minutes}m]))"
    )


def error_ratio_expr(metric_map: dict[str, dict[str, Any]], svc: str, minutes: int) -> str:
    inner = render(metric_map["error_ratio"]["promql"], svc)
    return f"avg_over_time(({inner})[{minutes}m:{STEP_S}s])"


def evaluate(prom: Prom, metric_map: dict[str, dict[str, Any]], minutes: int, end: float) -> list[Row]:
    rows = []
    for svc in SERVER_SIDE_SERVICES:
        rows.append(
            Row(
                svc,
                prom.scalar(error_ratio_expr(metric_map, svc, minutes), end),
                prom.scalar(restarts_expr(svc, minutes), end),
            )
        )
    return rows


def format_table(rows: list[Row]) -> str:
    def cell(value: float | None, fmt: str) -> str:
        return "no data" if value is None else format(value, fmt)

    lines = [f"{'service':<18} | {'error_ratio':<11} | {'restarts':<8} | result"]
    for r in rows:
        lines.append(
            f"{r.service:<18} | {cell(r.error_ratio, '.6f'):<11} | {cell(r.restarts, '.2f'):<8} | "
            f"{'PASS' if r.passed else 'FAIL'}"
        )
    return "\n".join(lines)


def collect_samples(
    prom: Prom, metric_map: dict[str, dict[str, Any]], start: float, end: float
) -> dict[str, list[float]]:
    """15 s range queries of `latency_p95` (every server-side service) and `kafka_consumer_lag`."""
    samples: dict[str, list[float]] = {}
    for svc in SERVER_SIDE_SERVICES:
        samples[f"latency_p95:{svc}"] = _points(
            prom.query_range(render(metric_map["latency_p95"]["promql"], svc), start, end, STEP_S)
        )
    samples[f"kafka_consumer_lag:{LAG_SERVICE}"] = _points(
        prom.query_range(render(metric_map["kafka_consumer_lag"]["promql"], LAG_SERVICE), start, end, STEP_S)
    )
    return samples


def _points(result: list[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    for series in result:
        for _, raw in series.get("values", []):
            v = float(raw)
            if math.isfinite(v):
                values.append(v)
    return values


def check_preconditions(context: str) -> list[str]:
    """Problems that make the run meaningless (empty list = the workload is at the WKL-004 state)."""
    problems: list[str] = []
    cm = run(
        ["kubectl", "--context", context, "-n", "shop", "get", "configmap", "flagd-config", "-o", "json"],
        check=False,
    )
    if cm.returncode != 0:
        problems.append(f"cannot read ConfigMap shop/flagd-config: {cm.stderr.strip()}")
    else:
        for name, text in json.loads(cm.stdout)["data"].items():
            flags = json.loads(text).get("flags", {}) if name.endswith(".json") else {}
            on = sorted(k for k, v in flags.items() if v.get("defaultVariant") != "off")
            if on:
                problems.append(f"flags with defaultVariant other than off in {name}: {', '.join(on)}")
    dep = run(
        ["kubectl", "--context", context, "-n", "shop", "get", "deployment", "load-generator", "-o", "json"],
        check=False,
    )
    if dep.returncode != 0:
        problems.append(f"cannot read Deployment shop/load-generator: {dep.stderr.strip()}")
    else:
        env = {
            e["name"]: e.get("value")
            for e in json.loads(dep.stdout)["spec"]["template"]["spec"]["containers"][0]["env"]
        }
        if env.get("LOCUST_USERS") != EXPECTED_LOCUST_USERS:
            problems.append(
                f"LOCUST_USERS is {env.get('LOCUST_USERS')!r}, expected {EXPECTED_LOCUST_USERS!r}"
            )
    return problems


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class PortForward:
    """`kubectl port-forward` to Prometheus, restarted on demand when the process has exited."""

    def __init__(self, context: str) -> None:
        self.context = context
        self.port = free_port()
        self.proc: subprocess.Popen[bytes] | None = None

    def ensure(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            return
        cmd = [
            "kubectl", "--context", self.context, "-n", "observability",
            "port-forward", "svc/prometheus-operated", f"{self.port}:9090",
        ]  # fmt: skip
        # S603: argument list, no shell, fixed command (GEN-041).
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603
        time.sleep(3)

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def progress_line(prom: Prom, metric_map: dict[str, dict[str, Any]], elapsed_min: float, minutes: int) -> str:
    worst_svc, worst = "-", 0.0
    for svc in SERVER_SIDE_SERVICES:
        v = prom.scalar(render(metric_map["error_ratio"]["promql"].replace("[1m]", "[5m]"), svc)) or 0.0
        if v > worst:
            worst_svc, worst = svc, v
    window = max(1, int(elapsed_min))
    restarted = prom.query(
        f'sum by (pod)(increase(kube_pod_container_status_restarts_total{{namespace="shop"}}[{window}m])) > 0'
    )
    names = ",".join(sorted(r["metric"].get("pod", "?") for r in restarted)) or "none"
    head = f"[{elapsed_min:5.1f}/{minutes} min]"
    return f"{head} max 5m error_ratio {worst:.4f} ({worst_svc}); restarted pods: {names}"


def main(argv: list[str] | None = None, *, sleep: Callable[[float], None] = time.sleep) -> int:
    ap = argparse.ArgumentParser(description="WKL-004 baseline health gate")
    ap.add_argument("--minutes", type=int, default=DEFAULT_MINUTES)
    ap.add_argument("--context", default=DEFAULT_CONTEXT)
    ap.add_argument("--prometheus-url", default=None)
    ap.add_argument("--poll-s", type=int, default=DEFAULT_POLL_S)
    ap.add_argument("--date", default=datetime.now(UTC).strftime("%Y-%m-%d"))
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument(
        "--skip-preconditions", action="store_true", help="skip the flag and load check (tests only)"
    )
    args = ap.parse_args(argv)
    if args.minutes < 1 or args.poll_s < 1:
        print("baseline_gate: --minutes and --poll-s must be >= 1", file=sys.stderr)
        return 2
    out_dir: Path = args.out_dir or REPO / "data/baseline" / args.date
    metric_map = load_metric_map()

    if not args.skip_preconditions:
        problems = check_preconditions(args.context)
        if problems:
            for p in problems:
                print(f"baseline_gate: precondition failed: {p}", file=sys.stderr)
            return 2

    forward = None if args.prometheus_url else PortForward(args.context)
    try:

        def client() -> PromClient:
            if forward is not None:
                forward.ensure()
            return PromClient(args.prometheus_url or forward.url)  # type: ignore[union-attr]

        try:
            client().query("up")
        except PromError as exc:
            print(f"baseline_gate: Prometheus unreachable: {exc}", file=sys.stderr)
            return 2
        start = time.time()
        deadline = start + args.minutes * 60
        failed_polls = 0
        print(
            f"baseline_gate: start {datetime.fromtimestamp(start, UTC).isoformat()}, "
            f"{args.minutes} min, poll {args.poll_s} s",
            flush=True,
        )
        while time.time() < deadline:
            sleep(min(args.poll_s, max(0.0, deadline - time.time())))
            try:
                print(
                    progress_line(client(), metric_map, (time.time() - start) / 60, args.minutes), flush=True
                )
            except PromError as exc:
                failed_polls += 1
                print(f"baseline_gate: poll failed ({failed_polls}): {exc}", flush=True)
        end = time.time()
        prom = client()
        rows = evaluate(prom, metric_map, args.minutes, end)
        samples = collect_samples(prom, metric_map, start, end)
    except PromError as exc:
        print(f"baseline_gate: Prometheus unreachable at the end of the run: {exc}", file=sys.stderr)
        return 2
    finally:
        if forward is not None:
            forward.stop()

    table = format_table(rows)
    print(table)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "samples.json").write_text(
        json.dumps(
            {"date": args.date, "minutes": args.minutes, "step_s": STEP_S, "samples": samples}, indent=1
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "report.json").write_text(
        json.dumps(
            {
                "date": args.date,
                "minutes": args.minutes,
                "failed_polls": failed_polls,
                "rows": [
                    {
                        "service": r.service,
                        "error_ratio": r.error_ratio,
                        "restarts": r.restarts,
                        "pass": r.passed,
                    }
                    for r in rows
                ],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"baseline_gate: wrote {out_dir}/samples.json and report.json; failed polls: {failed_polls}")
    if all(r.passed for r in rows):
        print("baseline_gate: PASS")
        return 0
    print("baseline_gate: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
