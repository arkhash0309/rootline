"""RFC 9457 problem+json (API-002)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rootline_common.ids import new_ulid
from rootline_common.logging import request_id_var

PROBLEM_CODES: dict[str, int] = {
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
log = logging.getLogger("rootline.problem")


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
        self.extra, self.headers = extra or {}, headers or {}


def _body(
    request: Request,
    code: str,
    status: int,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": f"https://rootline.dev/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": request_id_var.get() or new_ulid(),
        **(extra or {}),
    }


def _resp(body: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        body, status_code=body["status"], media_type="application/problem+json", headers=headers
    )


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def _problem(request: Request, exc: Problem) -> JSONResponse:
        return _resp(_body(request, exc.code, exc.status, exc.title, exc.detail, exc.extra), exc.headers)

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
        log.exception("unhandled error")
        return _resp(_body(request, "internal", 500, "Internal error", "unexpected error"))
