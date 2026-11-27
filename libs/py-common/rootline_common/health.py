"""/healthz, /readyz, /metrics (ARC-020)."""

from collections.abc import Awaitable, Callable, Mapping

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


async def _metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def make_metrics_route() -> APIRoute:
    """Return the `GET /metrics` route (Prometheus text exposition format, ARC-020)."""
    return APIRoute("/metrics", _metrics, methods=["GET"], include_in_schema=False)


def make_health_router(checks: Mapping[str, Callable[[], Awaitable[bool]]]) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/readyz", include_in_schema=False)
    async def readyz() -> JSONResponse:
        failing = []
        for name, check in checks.items():
            try:
                ok = await check()
            except Exception:  # any exception from a readiness check means not ready (ARC-020, ADR 0040)
                ok = False
            if not ok:
                failing.append(name)
        return JSONResponse(
            {"failing": failing} if failing else {"status": "ready"},
            status_code=503 if failing else 200,
        )

    router.routes.append(make_metrics_route())
    return router
