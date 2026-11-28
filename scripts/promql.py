"""Prometheus HTTP API client and metric-map helpers (WKL-022, WKL-030; W1-T13).

`PromClient(base_url)` wraps two endpoints of the Prometheus HTTP API (standard library only):

| Method | Endpoint | Arguments | Returns |
|---|---|---|---|
| `query(expr, ts=None)` | `GET /api/v1/query` | `expr` PromQL; `ts` Unix s, `None` = now | `data.result`: list of `{"metric": {}, "value": [ts, "v"]}` |
| `query_range(expr, start, end, step_s)` | `GET /api/v1/query_range` | `start`, `end` Unix s; `step_s` > 0 | `data.result`: list of `{"metric": {}, "values": [[ts, "v"]]}` |
| `scalar(expr, ts=None)` | `GET /api/v1/query` | as `query` | first sample as `float`; `None` when empty or `NaN` |

Errors: HTTP status other than 200, a connection failure, a body that is not JSON, or `status != "success"`
raises `PromError` (message holds the URL and the Prometheus `error` text). The client sets a timeout of
`timeout_s` seconds (default 30) per request and never retries.

`load_metric_map(path)` reads `metric-map.yaml` (schema in that file's header) and `render(template, svc, wl)`
replaces the placeholders `$svc` and `$wl` (`wl` defaults to `svc`; the two are equal for every kept
component, `wiki/components/telemetry.md` finding F5).
"""  # noqa: E501 - markdown tables in the module docstring

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

DEFAULT_METRIC_MAP = Path(__file__).resolve().parents[1] / "deploy/charts/observability/files/metric-map.yaml"
# WKL-030: the metric keys, in the order of the spec table.
METRIC_KEYS = (
    "request_rate",
    "error_ratio",
    "latency_p50",
    "latency_p95",
    "latency_p99",
    "cpu_usage",
    "memory_working_set",
    "restarts",
    "kafka_consumer_lag",
    "gc_pause",
)


class PromError(RuntimeError):
    """A Prometheus request failed (transport error, non-200 status, or `status != success`)."""


class PromClient:
    def __init__(self, base_url: str, timeout_s: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def _get(self, path: str, params: dict[str, str]) -> Any:
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        if not url.startswith(("http://", "https://")):
            raise PromError(f"unsupported URL scheme: {url}")
        try:
            # S310: the scheme is checked above (http or https only).
            with urllib.request.urlopen(url, timeout=self.timeout_s) as resp:  # noqa: S310
                body = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise PromError(f"{url}: HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PromError(f"{url}: {exc}") from exc
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise PromError(f"{url}: response is not JSON") from exc
        if not isinstance(doc, dict) or doc.get("status") != "success":
            error = doc.get("error", "unknown error") if isinstance(doc, dict) else "unexpected body"
            raise PromError(f"{url}: {error}")
        return doc["data"]["result"]

    def query(self, expr: str, ts: float | None = None) -> list[dict[str, Any]]:
        params = {"query": expr}
        if ts is not None:
            params["time"] = f"{ts:.3f}"
        result: list[dict[str, Any]] = self._get("/api/v1/query", params)
        return result

    def query_range(self, expr: str, start: float, end: float, step_s: float) -> list[dict[str, Any]]:
        if step_s <= 0:
            raise ValueError("step_s must be > 0")
        params = {"query": expr, "start": f"{start:.3f}", "end": f"{end:.3f}", "step": f"{step_s:g}"}
        result: list[dict[str, Any]] = self._get("/api/v1/query_range", params)
        return result

    def scalar(self, expr: str, ts: float | None = None) -> float | None:
        result = self.query(expr, ts)
        if not result:
            return None
        value = float(result[0]["value"][1])
        return None if math.isnan(value) else value


def load_metric_map(path: Path = DEFAULT_METRIC_MAP) -> dict[str, dict[str, Any]]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    metrics: dict[str, dict[str, Any]] = doc["metrics"]
    return metrics


def render(template: str, svc: str, wl: str | None = None) -> str:
    """Substitute `$svc` and `$wl` in a metric-map PromQL template."""
    return template.replace("$svc", svc).replace("$wl", wl if wl is not None else svc)
