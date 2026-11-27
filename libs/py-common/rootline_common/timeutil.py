"""Time helpers: RFC 3339 UTC with Z (API-006, MCP-002, PG-24)."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_rfc3339(dt: datetime, *, ms: bool = True) -> str:
    if dt.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {dt.isoformat()}")
    dt = dt.astimezone(UTC)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{dt.microsecond // 1000:03d}Z" if ms else f"{base}Z"


def parse_rfc3339(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {text}")
    return dt.astimezone(UTC)
