"""Verifies API-004 and PG-24 D2, D4."""

import asyncio

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from rootline_common.ids import is_ulid
from rootline_common.logging import request_id_var
from rootline_common.requestid import RequestIdMiddleware
from starlette.types import Message, Receive, Scope, Send

RID_A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
RID_B = "01BX5ZZKBKACTAV9WEVGEMMVRZ"


def make() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/x")
    def x(request: Request) -> dict[str, object]:
        return {"rid": request_id_var.get(), "state": request.state.request_id}

    return TestClient(app)


def call_raw(headers: list[tuple[bytes, bytes]]) -> tuple[list[Message], Scope]:
    """Drive the middleware with a raw ASGI scope (bytes headers, no client re-encoding)."""
    sent: list[Message] = []
    scope: Scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(RequestIdMiddleware(app)(scope, receive, send))
    return sent, scope


def test_valid_incoming_id_is_kept() -> None:
    r = make().get("/x", headers={"X-Request-Id": RID_A})
    assert r.headers["X-Request-Id"] == RID_A == r.json()["rid"] == r.json()["state"]


def test_invalid_incoming_id_is_replaced() -> None:
    r = make().get("/x", headers={"X-Request-Id": "abc"})
    assert r.headers["X-Request-Id"] != "abc" and is_ulid(r.headers["X-Request-Id"])
    assert r.json()["state"] == r.headers["X-Request-Id"]


def test_non_utf8_incoming_id_is_replaced() -> None:
    sent, scope = call_raw([(b"x-request-id", b"\xff\xfe01ARZ3NDEKTSV4RRFFQ69G5F")])
    rid = dict(sent[0]["headers"])[b"x-request-id"].decode()
    assert is_ulid(rid) and scope["state"]["request_id"] == rid


def test_first_incoming_header_wins() -> None:
    sent, scope = call_raw([(b"x-request-id", RID_A.encode()), (b"x-request-id", RID_B.encode())])
    assert dict(sent[0]["headers"])[b"x-request-id"] == RID_A.encode()
    assert scope["state"]["request_id"] == RID_A
