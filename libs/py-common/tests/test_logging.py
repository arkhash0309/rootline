"""Verifies OBS-001 log format."""

import json
import logging

import pytest
from rootline_common.logging import configure_logging, investigation_id_var, request_id_var


def test_json_log_line(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("api", "INFO")
    request_id_var.set("01ARZ3NDEKTSV4RRFFQ69G5FAV")
    investigation_id_var.set(None)
    logging.getLogger("rootline.test").info("hello %s", "world")
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["msg"] == "hello world"
    assert line["level"] == "INFO"
    assert line["logger"] == "rootline.test"
    assert line["component"] == "api"
    assert line["request_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert "investigation_id" not in line
    assert line["ts"].endswith("Z")
