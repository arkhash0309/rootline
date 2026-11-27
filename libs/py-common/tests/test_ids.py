"""Verifies GEN glossary 'ULID', OBS-020 (trace id mapping)."""

from rootline_common.ids import is_ulid, new_ulid, ulid_to_trace_id


def test_new_ulid_shape() -> None:
    u = new_ulid()
    assert len(u) == 26 and is_ulid(u)


def test_is_ulid_rejects() -> None:
    assert not is_ulid("not-a-ulid")
    assert not is_ulid("01ARZ3NDEKTSV4RRFFQ69G5FAI")  # I is not Crockford


def test_trace_id_is_128_bit_hex() -> None:
    from ulid import ULID

    u = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert ulid_to_trace_id(u) == ULID.from_str(u).bytes.hex()
    assert len(ulid_to_trace_id(new_ulid())) == 32
