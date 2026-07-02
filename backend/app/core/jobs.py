"""Generic background-job store, backed by the app's existing Redis.

Lets an endpoint return immediately with a job ID while the real (slow)
work runs in a FastAPI BackgroundTask, instead of holding one HTTP request
open for the duration of a real AI call. Most production load balancers and
reverse proxies kill idle connections well before a slow AI call finishes
(30-100s defaults are common), regardless of what timeout our own app code
is configured with - this sidesteps that entirely by never holding a
request open more than a couple seconds."""

import uuid
from enum import Enum

from pydantic import BaseModel

from app.integrations.redis.client import get_redis_client

_JOB_KEY_PREFIX = "job:"
_JOB_TTL_SECONDS = 3600  # plenty of time for a client to poll and collect the result


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRecord(BaseModel):
    id: str
    status: JobStatus
    result: dict | None = None
    error: str | None = None
    error_code: str | None = None


def _key(job_id: str) -> str:
    return f"{_JOB_KEY_PREFIX}{job_id}"


async def create_job() -> str:
    job_id = str(uuid.uuid4())
    record = JobRecord(id=job_id, status=JobStatus.PENDING)
    await get_redis_client().set(_key(job_id), record.model_dump_json(), ex=_JOB_TTL_SECONDS)
    return job_id


async def set_job_running(job_id: str) -> None:
    await _update(job_id, status=JobStatus.RUNNING)


async def set_job_completed(job_id: str, result: dict) -> None:
    await _update(job_id, status=JobStatus.COMPLETED, result=result)


async def set_job_failed(job_id: str, error: str, error_code: str = "INTERNAL_ERROR") -> None:
    await _update(job_id, status=JobStatus.FAILED, error=error, error_code=error_code)


async def get_job(job_id: str) -> JobRecord | None:
    raw = await get_redis_client().get(_key(job_id))
    if raw is None:
        return None
    return JobRecord.model_validate_json(raw)


async def _update(job_id: str, **fields) -> None:
    existing = await get_job(job_id)
    if existing is None:
        return  # job expired or never existed - nothing to update
    updated = existing.model_copy(update=fields)
    await get_redis_client().set(_key(job_id), updated.model_dump_json(), ex=_JOB_TTL_SECONDS)
