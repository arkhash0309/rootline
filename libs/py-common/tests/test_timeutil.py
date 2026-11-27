"""Verifies API-006, MCP-002 timestamp format and PG-24 D6."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from rootline_common.timeutil import parse_rfc3339, to_rfc3339, utcnow


def test_utcnow_is_aware_utc() -> None:
    assert utcnow().tzinfo is UTC


def test_to_rfc3339_ms_z() -> None:
    dt = datetime(2026, 11, 30, 9, 5, 7, 123456, tzinfo=UTC)
    assert to_rfc3339(dt) == "2026-11-30T09:05:07.123Z"
    assert to_rfc3339(dt, ms=False) == "2026-11-30T09:05:07Z"


def test_to_rfc3339_converts_other_zones() -> None:
    dt = datetime(2026, 11, 30, 14, 35, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert to_rfc3339(dt) == "2026-11-30T09:05:00.000Z"


def test_parse_roundtrip() -> None:
    assert parse_rfc3339("2026-11-30T09:05:07.123Z") == datetime(2026, 11, 30, 9, 5, 7, 123000, tzinfo=UTC)


def test_to_rfc3339_rejects_naive() -> None:
    with pytest.raises(ValueError, match=r"^naive datetime not allowed: 2026-11-30T09:05:07$"):
        to_rfc3339(datetime(2026, 11, 30, 9, 5, 7))


def test_parse_rejects_missing_offset() -> None:
    with pytest.raises(ValueError, match=r"^naive datetime not allowed: 2026-11-30T09:05:07$"):
        parse_rfc3339("2026-11-30T09:05:07")
