from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_envelope
from app.database.deps import get_db
from app.integrations.redis.client import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return success_envelope({"status": "ok"}, "Service is healthy")


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):
    checks = {"database": "unknown", "redis": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    overall_ok = all(v == "ok" for v in checks.values())
    return success_envelope(
        {"status": "ok" if overall_ok else "degraded", "checks": checks},
        "Readiness check completed",
    )
