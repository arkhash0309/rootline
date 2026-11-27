"""Verifies API-002."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from rootline_common.problem import PROBLEM_CODES, Problem, install_problem_handlers


def make_app() -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)

    class Body(BaseModel):
        n: int

    @app.get("/boom")
    def boom() -> None:
        raise Problem("invalid_transition", 409, "Invalid transition", "queued -> merged")

    @app.post("/validate")
    def validate(body: Body) -> dict[str, Any]:
        return {}

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret detail")

    return app


def test_problem_shape() -> None:
    r = TestClient(make_app()).get("/boom", headers={"X-Request-Id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"})
    assert r.status_code == 409
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body == {
        "type": "https://rootline.dev/problems/invalid_transition",
        "title": "Invalid transition",
        "status": 409,
        "detail": "queued -> merged",
        "instance": "/boom",
        "code": "invalid_transition",
        "request_id": body["request_id"],
    }


def test_validation_error_has_errors_list() -> None:
    r = TestClient(make_app()).post("/validate", json={"n": "x"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    assert r.json()["errors"][0]["loc"] == ["body", "n"]


def test_internal_error_hides_detail() -> None:
    r = TestClient(make_app(), raise_server_exceptions=False).get("/crash")
    assert r.status_code == 500 and r.json()["code"] == "internal"
    assert "secret detail" not in r.text


def test_codes_table() -> None:
    assert PROBLEM_CODES == {
        "unauthenticated": 401,
        "insufficient_user_authentication": 401,
        "forbidden": 403,
        "not_found": 404,
        "validation_error": 422,
        "invalid_transition": 409,
        "conflict": 409,
        "separation_of_duties": 403,
        "rate_limited": 429,
        "lab_busy": 409,
        "internal": 500,
    }
