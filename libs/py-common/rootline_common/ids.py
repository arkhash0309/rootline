"""ULID helpers (spec §2 'ULID', OBS-020)."""

import re

from ulid import ULID

_CROCKFORD = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def new_ulid() -> str:
    return str(ULID())


def is_ulid(value: str) -> bool:
    return bool(_CROCKFORD.fullmatch(value or ""))


def ulid_to_trace_id(ulid: str) -> str:
    return ULID.from_str(ulid).bytes.hex()
