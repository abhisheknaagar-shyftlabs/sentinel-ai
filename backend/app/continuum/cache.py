"""Content-hash cache for Continuum calls. If the exact same instructions +
input_text + output_schema are submitted again, skip the AI call entirely
and return the previous result - no reason to re-pay for (and re-wait on) an
identical PR review or branch comparison.

Redis-backed (reuses the app's existing Redis instance, not a new
dependency) so it survives restarts, unlike an in-memory dict. Purely an
optimization: any Redis failure degrades to a cache miss, never breaks the
underlying call - same "gracefully degrade" convention as the rest of the
app's optional infra (AWS cost, Docker health).

Self-invalidating by construction: the cache key includes the full
instructions text, so changing a prompt (e.g. tightening SYSTEM_PROMPT) or
the schema automatically produces a new key - no manual cache-busting
needed when prompts evolve during development."""

import hashlib

from pydantic import BaseModel

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.integrations.redis.client import get_redis_client

logger = get_logger(__name__)

_CACHE_KEY_PREFIX = "continuum:cache:"


def _build_cache_key(
    agent_name: str, instructions: str, input_text: str, output_schema: type[BaseModel] | None
) -> str:
    schema_name = output_schema.__name__ if output_schema else "none"
    raw = f"{agent_name}:{schema_name}:{instructions}:{input_text}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{_CACHE_KEY_PREFIX}{digest}"


async def get_cached_response(
    agent_name: str, instructions: str, input_text: str, output_schema: type[BaseModel] | None
) -> BaseModel | str | None:
    key = _build_cache_key(agent_name, instructions, input_text, output_schema)
    try:
        raw = await get_redis_client().get(key)
    except Exception as exc:  # noqa: BLE001 - cache is best-effort, never fatal
        logger.warning("continuum_cache_read_failed", extra={"agent": agent_name, "error": str(exc)})
        return None

    if raw is None:
        return None

    logger.info("continuum_cache_hit", extra={"agent": agent_name})
    if output_schema is not None:
        return output_schema.model_validate_json(raw)
    return raw


async def set_cached_response(
    agent_name: str,
    instructions: str,
    input_text: str,
    output_schema: type[BaseModel] | None,
    value: BaseModel | str,
) -> None:
    key = _build_cache_key(agent_name, instructions, input_text, output_schema)
    payload = value.model_dump_json() if isinstance(value, BaseModel) else value
    ttl_seconds = get_settings().continuum_cache_ttl_seconds
    try:
        await get_redis_client().set(key, payload, ex=ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("continuum_cache_write_failed", extra={"agent": agent_name, "error": str(exc)})
