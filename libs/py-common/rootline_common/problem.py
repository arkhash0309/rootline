"""RFC 9457 problem+json (API-002, PG-24)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from rootline_common.ids import new_ulid
from rootline_common.logging import request_id_var

PROBLEM_CODES: dict[str, int] = {
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
# HTTPException status -> (code, title) (PG-24 D3). Any other status: code "internal", status kept.
HTTP_STATUS_PROBLEMS: dict[int, tuple[str, str]] = {
    401: ("unauthenticated", "Unauthenticated"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not found"),
    405: ("method_not_allowed", "Method not allowed"),
}
# Body keys that `extra` can never set (PG-24 D5); they are dropped silently.
RESERVED_PROBLEM_KEYS: frozenset[str] = frozenset(
    {"type", "title", "status", "detail", "instance", "code", "request_id"}
)
log = logging.getLogger("rootline.problem")


def _clean(extra: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (extra or {}).items() if k not in RESERVED_PROBLEM_KEYS}


class Problem(Exception):
    def __init__(
        self,
        code: str,
        status: int,
        title: str,
        detail: str = "",
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail or title)
        self.code, self.status, self.title, self.detail = code, status, title, detail[:500]
        self.extra, self.headers = _clean(extra), headers or {}


def _request_id(request: Request) -> str:
    """scope["state"]["request_id"] (RequestIdMiddleware), else request_id_var, else a new ULID (PG-24 D2)."""
    state = request.scope.get("state")
    rid = state.get("request_id") if isinstance(state, dict) else None
    if isinstance(rid, str) and rid:
        return rid
    return request_id_var.get() or new_ulid()


def _body(
    request: Request,
    code: str,
    status: int,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "type": f"https://rootline.dev/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": request_id or _request_id(request),
        **_clean(extra),
    }


def _resp(body: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        body, status_code=body["status"], media_type="application/problem+json", headers=headers
    )


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def _problem(request: Request, exc: Problem) -> JSONResponse:
        return _resp(_body(request, exc.code, exc.status, exc.title, exc.detail, exc.extra), exc.headers)

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> Response:
        headers = dict(exc.headers) if exc.headers else None
        if exc.status_code in (204, 304):  # no body allowed (RFC 9110 §15.3.5, §15.4.5)
            return Response(status_code=exc.status_code, headers=headers)
        mapped = HTTP_STATUS_PROBLEMS.get(exc.status_code)
        if mapped is None:
            log.warning("unmapped HTTPException status %d", exc.status_code)
            body = _body(request, "internal", exc.status_code, "Internal error", "unexpected error")
        else:
            detail = exc.detail[:500] if isinstance(exc.detail, str) else ""
            body = _body(request, mapped[0], exc.status_code, mapped[1], detail)
        return _resp(body, headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return _resp(
            _body(
                request,
                "validation_error",
                422,
                "Validation error",
                "request body or query is invalid",
                {"errors": errors},
            )
        )

    @app.exception_handler(Exception)
    async def _internal(request: Request, exc: Exception) -> JSONResponse:
        # Runs in ServerErrorMiddleware, outside RequestIdMiddleware: request_id_var is already
        # reset and the response bypasses the middleware's send wrapper (PG-24 D2).
        rid = _request_id(request)
        token = request_id_var.set(rid)
        try:
            log.error("unhandled error", exc_info=exc)
        finally:
            request_id_var.reset(token)
        return _resp(
            _body(request, "internal", 500, "Internal error", "unexpected error", request_id=rid),
            {"X-Request-Id": rid},
        )
