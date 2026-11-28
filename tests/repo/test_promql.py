"""Verifies WKL-022 and WKL-030 (PromClient and metric-map helpers, W1-T13)."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from scripts.promql import METRIC_KEYS, PromClient, PromError, load_metric_map, render


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _serve(monkeypatch: pytest.MonkeyPatch, body: bytes | Exception, seen: list[str] | None = None) -> None:
    def fake_urlopen(url: str, timeout: float) -> FakeResponse:
        if seen is not None:
            seen.append(url)
        if isinstance(body, Exception):
            raise body
        return FakeResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def _ok(result: list[dict[str, Any]]) -> bytes:
    return json.dumps({"status": "success", "data": {"resultType": "vector", "result": result}}).encode()


def test_query_builds_url_and_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-022: `query` calls /api/v1/query with the expression and the time and returns data.result."""
    seen: list[str] = []
    result = [{"metric": {}, "value": [1.0, "2"]}]
    _serve(monkeypatch, _ok(result), seen)
    assert PromClient("http://prom:9090/").query("up", 12.5) == result
    assert seen[0].startswith("http://prom:9090/api/v1/query?") and "query=up" in seen[0]
    assert "time=12.500" in seen[0]


def test_http_error_maps_to_prom_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-022: an HTTP error status raises PromError with the status code and the body text."""
    err = urllib.error.HTTPError("http://prom", 422, "bad", None, io.BytesIO(b"parse error"))  # type: ignore[arg-type]
    _serve(monkeypatch, err)
    with pytest.raises(PromError, match="HTTP 422: parse error"):
        PromClient("http://prom").query("up{")


def test_connection_failure_maps_to_prom_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-022: a connection failure or timeout raises PromError."""
    _serve(monkeypatch, urllib.error.URLError("refused"))
    with pytest.raises(PromError, match="refused"):
        PromClient("http://prom").query("up")
    _serve(monkeypatch, TimeoutError("timed out"))
    with pytest.raises(PromError, match="timed out"):
        PromClient("http://prom").query("up")


def test_non_json_body_maps_to_prom_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-022: a body that is not JSON raises PromError."""
    _serve(monkeypatch, b"<html>")
    with pytest.raises(PromError, match="not JSON"):
        PromClient("http://prom").query("up")


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (json.dumps({"status": "error", "error": "boom"}).encode(), "boom"),
        (json.dumps({"status": "error"}).encode(), "unknown error"),
        (json.dumps([1, 2]).encode(), "unexpected body"),
    ],
)
def test_status_not_success_maps_to_prom_error(
    monkeypatch: pytest.MonkeyPatch, body: bytes, message: str
) -> None:
    """WKL-022: `status != success` and a non-object body raise PromError."""
    _serve(monkeypatch, body)
    with pytest.raises(PromError, match=message):
        PromClient("http://prom").query("up")


def test_unsupported_scheme_is_rejected() -> None:
    """WKL-022: only http and https URLs are used."""
    with pytest.raises(PromError, match="unsupported URL scheme"):
        PromClient("file:///etc").query("up")


def test_scalar_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-022: scalar returns the first sample, None for an empty result and None for NaN."""
    _serve(monkeypatch, _ok([{"metric": {}, "value": [1, "0.25"]}]))
    assert PromClient("http://prom").scalar("x") == 0.25
    _serve(monkeypatch, _ok([]))
    assert PromClient("http://prom").scalar("x") is None
    _serve(monkeypatch, _ok([{"metric": {}, "value": [1, "NaN"]}]))
    assert PromClient("http://prom").scalar("x") is None


def test_query_range_checks_step_and_sends_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKL-022: step_s <= 0 raises ValueError; otherwise start, end and step are sent."""
    with pytest.raises(ValueError, match="step_s"):
        PromClient("http://prom").query_range("up", 0, 10, 0)
    seen: list[str] = []
    _serve(monkeypatch, _ok([]), seen)
    assert PromClient("http://prom").query_range("up", 1, 2, 15) == []
    assert "/api/v1/query_range?" in seen[0] and "step=15" in seen[0] and "start=1.000" in seen[0]


def test_metric_map_has_the_ten_keys_and_render_substitutes() -> None:
    """WKL-030: metric-map.yaml has the ten keys; render replaces $svc and $wl."""
    metric_map = load_metric_map()
    assert tuple(metric_map) == METRIC_KEYS
    assert render('a{s="$svc",p="$wl"}', "cart") == 'a{s="cart",p="cart"}'
    assert render("$svc-$wl", "a", "b") == "a-b"
