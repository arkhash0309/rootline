"""Verifies ARC-020."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rootline_common.health import make_health_router, make_metrics_route


async def ok() -> bool:
    return True


async def down() -> bool:
    return False


def test_ready_and_live() -> None:
    app = FastAPI()
    app.include_router(make_health_router({"db": ok, "keycloak": down}))
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200
    r = c.get("/readyz")
    assert r.status_code == 503 and r.json() == {"failing": ["keycloak"]}
    assert c.get("/metrics").status_code == 200


def test_ready_when_all_checks_pass() -> None:
    app = FastAPI()
    app.include_router(make_health_router({"db": ok}))
    r = TestClient(app).get("/readyz")
    assert r.status_code == 200 and r.json() == {"status": "ready"}


def test_check_exception_counts_as_failing() -> None:
    async def boom() -> bool:
        raise ConnectionError

    app = FastAPI()
    app.include_router(make_health_router({"db": boom}))
    assert TestClient(app).get("/readyz").json() == {"failing": ["db"]}


def test_metrics_route_standalone() -> None:
    app = FastAPI()
    app.router.routes.append(make_metrics_route())
    r = TestClient(app).get("/metrics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
