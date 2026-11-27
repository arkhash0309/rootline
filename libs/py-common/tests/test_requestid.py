"""Verifies API-004."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rootline_common.ids import is_ulid
from rootline_common.logging import request_id_var
from rootline_common.requestid import RequestIdMiddleware


def make() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/x")
    def x() -> dict[str, str | None]:
        return {"rid": request_id_var.get()}

    return TestClient(app)


def test_valid_incoming_id_is_kept() -> None:
    r = make().get("/x", headers={"X-Request-Id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"})
    assert r.headers["X-Request-Id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV" == r.json()["rid"]


def test_invalid_incoming_id_is_replaced() -> None:
    r = make().get("/x", headers={"X-Request-Id": "abc"})
    assert r.headers["X-Request-Id"] != "abc" and is_ulid(r.headers["X-Request-Id"])
