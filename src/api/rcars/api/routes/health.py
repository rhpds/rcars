from __future__ import annotations

from fastapi import APIRouter, Request

from rcars.api.schemas import HealthResponse, ReadinessResponse

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    response_model=HealthResponse,
    openapi_extra={"security": []},
)
async def health():
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Checks database and Redis connectivity. Returns 'degraded' if either is unreachable.",
    response_model=ReadinessResponse,
    openapi_extra={"security": []},
)
async def readiness(request: Request):
    db = request.app.state.db
    redis = request.app.state.redis
    checks = {"database": False, "redis": False}
    try:
        with db.pool.connection() as conn:
            conn.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        pass
    try:
        await redis.ping()
        checks["redis"] = True
    except Exception:
        pass

    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
