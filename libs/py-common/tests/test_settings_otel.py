"""Verifies OBS-001 (tracing is a no-op without an endpoint) and the base settings contract."""

import pytest
from opentelemetry import trace
from pydantic import ValidationError
from rootline_common.otel import setup_tracing
from rootline_common.settings import BaseServiceSettings


def test_setup_tracing_noop_without_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    setup_tracing("api")
    assert trace.get_tracer_provider().__class__.__name__ == "ProxyTracerProvider"


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ROOTLINE_ENV", "LOG_LEVEL", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    s = BaseServiceSettings()
    assert (s.rootline_env, s.log_level, s.database_url) == ("local", "INFO", None)


def test_settings_reads_env_and_rejects_unknown_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROOTLINE_ENV", "ci")
    assert BaseServiceSettings().rootline_env == "ci"
    monkeypatch.setenv("ROOTLINE_ENV", "prod")
    with pytest.raises(ValidationError):
        BaseServiceSettings()
