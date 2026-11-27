"""Verifies API-002, API-004 (request ID on 500) and PG-24 D2, D3, D5."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from rootline_common.ids import is_ulid
from rootline_common.logging import configure_logging
from rootline_common.problem import (
    HTTP_STATUS_PROBLEMS,
    PROBLEM_CODES,
    Problem,
    install_problem_handlers,
)
from rootline_common.requestid import RequestIdMiddleware
from starlette.exceptions import HTTPException

RID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def make_app() -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)

    class Body(BaseModel):
        n: int

    @app.get("/boom")
    def boom() -> None:
        raise Problem("invalid_transition", 409, "Invalid transition", "queued -> merged")

    @app.post("/validate")
    def validate(body: Body) -> dict[str, object]:
        return {}

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret detail")

    @app.get("/auth")
    def auth() -> None:
        raise HTTPException(401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/teapot")
    def teapot() -> None:
        raise HTTPException(418, detail="teapot detail")

    @app.get("/extra")
    def extra() -> None:
        raise Problem(
            "conflict",
            409,
            "Conflict",
            "key reused",
            extra={"status": 200, "code": "x", "request_id": "y", "hint": "h"},
        )

    return app


def make_app_with_request_id() -> FastAPI:
    app = make_app()
    app.add_middleware(RequestIdMiddleware)
    return app


def test_problem_shape() -> None:
    r = TestClient(make_app()).get("/boom", headers={"X-Request-Id": RID})
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


def test_internal_error_carries_incoming_request_id(capsys: pytest.CaptureFixture[str]) -> None:
    """PG-24 D2: header, body request_id, incoming X-Request-Id and the log line agree."""
    configure_logging("test", "INFO")
    c = TestClient(make_app_with_request_id(), raise_server_exceptions=False)
    r = c.get("/crash", headers={"X-Request-Id": RID})
    assert r.status_code == 500
    assert r.headers.get_list("x-request-id") == [RID]
    assert r.json()["request_id"] == RID
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{")]
    assert [x["request_id"] for x in lines if x["logger"] == "rootline.problem"] == [RID]


def test_internal_error_generated_request_id_matches() -> None:
    c = TestClient(make_app_with_request_id(), raise_server_exceptions=False)
    r = c.get("/crash")
    assert r.headers.get_list("x-request-id") == [r.json()["request_id"]]
    assert is_ulid(r.json()["request_id"])


def test_not_found_is_problem() -> None:
    r = TestClient(make_app_with_request_id()).get("/nope", headers={"X-Request-Id": RID})
    assert r.status_code == 404 and r.headers["content-type"] == "application/problem+json"
    assert r.json() == {
        "type": "https://rootline.dev/problems/not_found",
        "title": "Not found",
        "status": 404,
        "detail": "Not Found",
        "instance": "/nope",
        "code": "not_found",
        "request_id": RID,
    }
    assert r.headers.get_list("x-request-id") == [RID]


def test_method_not_allowed_keeps_allow_header() -> None:
    r = TestClient(make_app()).post("/boom")
    assert r.status_code == 405 and r.headers["allow"] == "GET"
    assert (r.json()["code"], r.json()["title"]) == ("method_not_allowed", "Method not allowed")


def test_http_401_maps_to_unauthenticated_and_keeps_headers() -> None:
    r = TestClient(make_app()).get("/auth")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    body = r.json()
    assert (body["code"], body["title"], body["detail"]) == (
        "unauthenticated",
        "Unauthenticated",
        "Not authenticated",
    )


def test_unmapped_http_status_is_internal_with_status_kept() -> None:
    r = TestClient(make_app()).get("/teapot")
    assert r.status_code == 418 and r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert (body["status"], body["code"], body["title"], body["detail"]) == (
        418,
        "internal",
        "Internal error",
        "unexpected error",
    )
    assert "teapot detail" not in r.text


def test_reserved_extra_keys_are_dropped() -> None:
    r = TestClient(make_app()).get("/extra", headers={"X-Request-Id": RID})
    body = r.json()
    assert r.status_code == 409
    assert (body["status"], body["code"], body["hint"]) == (409, "conflict", "h")
    assert body["request_id"] != "y"
    assert Problem("conflict", 409, "Conflict", extra={"title": "x", "hint": "h"}).extra == {"hint": "h"}


def test_codes_table() -> None:
    assert PROBLEM_CODES == {
        "unauthenticated": 401,
        "insufficient_user_authentication": 401,
        "forbidden": 403,
        "not_found": 404,
        "method_not_allowed": 405,
        "validation_error": 422,
        "invalid_transition": 409,
        "conflict": 409,
        "separation_of_duties": 403,
        "rate_limited": 429,
        "lab_busy": 409,
        "internal": 500,
    }
    assert HTTP_STATUS_PROBLEMS == {
        401: ("unauthenticated", "Unauthenticated"),
        403: ("forbidden", "Forbidden"),
        404: ("not_found", "Not found"),
        405: ("method_not_allowed", "Method not allowed"),
    }
    assert all(PROBLEM_CODES[code] == status for status, (code, _) in HTTP_STATUS_PROBLEMS.items())
