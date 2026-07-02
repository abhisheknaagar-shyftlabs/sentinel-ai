"""Direct-provider fallback for when Continuum/the Smart Gateway doesn't
respond fast enough for a live demo. Lives inside app/continuum/ specifically
so the hard rule "no router/service/agent imports a model SDK directly"
still holds - this is the orchestration layer's own second and third path,
not a bypass of it. Only ContinuumClient (via this module) ever imports
openai/anthropic."""

import asyncio

from pydantic import BaseModel

from app.config.settings import Settings
from app.continuum.exceptions import ContinuumUnavailableError, MalformedResponseError
from app.core.logging import get_logger

logger = get_logger(__name__)

_FALLBACK_TIMEOUT_SECONDS = 20
_DEFAULT_MAX_TOKENS = 4096


async def run_with_fallback(
    instructions: str,
    input_text: str,
    output_schema: type[BaseModel] | None,
    max_tokens: int | None,
    settings: Settings,
    original_exc: Exception,
) -> BaseModel | str:
    """Tries OpenAI, then Anthropic, each bounded by its own timeout so the
    worst case is predictable. If neither is configured, re-raises the
    original Continuum failure unchanged - this feature is purely additive
    when no fallback key is set, not a behavior change."""
    if not settings.openai_api_key and not settings.anthropic_api_key:
        raise original_exc

    if settings.openai_api_key:
        try:
            return await asyncio.wait_for(
                _run_openai(instructions, input_text, output_schema, max_tokens, settings),
                timeout=_FALLBACK_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 - fall through to the next provider
            logger.warning("openai_fallback_failed", extra={"error": str(exc)})

    if settings.anthropic_api_key:
        try:
            return await asyncio.wait_for(
                _run_anthropic(instructions, input_text, output_schema, max_tokens, settings),
                timeout=_FALLBACK_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("anthropic_fallback_failed", extra={"error": str(exc)})

    raise ContinuumUnavailableError(
        f"Continuum failed ({original_exc}) and no fallback provider succeeded either"
    ) from original_exc


async def _run_openai(
    instructions: str,
    input_text: str,
    output_schema: type[BaseModel] | None,
    max_tokens: int | None,
    settings: Settings,
) -> BaseModel | str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": input_text},
    ]

    if output_schema is not None:
        completion = await client.chat.completions.parse(
            model=settings.openai_fallback_model,
            messages=messages,
            response_format=output_schema,
            max_completion_tokens=max_tokens or _DEFAULT_MAX_TOKENS,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise MalformedResponseError("OpenAI fallback did not return a parseable structured response")
        logger.info("fallback_served", extra={"provider": "openai", "model": settings.openai_fallback_model})
        return parsed

    completion = await client.chat.completions.create(
        model=settings.openai_fallback_model,
        messages=messages,
        max_completion_tokens=max_tokens or _DEFAULT_MAX_TOKENS,
    )
    logger.info("fallback_served", extra={"provider": "openai", "model": settings.openai_fallback_model})
    return completion.choices[0].message.content or ""


async def _run_anthropic(
    instructions: str,
    input_text: str,
    output_schema: type[BaseModel] | None,
    max_tokens: int | None,
    settings: Settings,
) -> BaseModel | str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    if output_schema is not None:
        response = await client.messages.parse(
            model=settings.anthropic_fallback_model,
            max_tokens=max_tokens or _DEFAULT_MAX_TOKENS,
            system=instructions,
            messages=[{"role": "user", "content": input_text}],
            output_format=output_schema,
        )
        parsed = response.parsed_output
        if parsed is None:
            raise MalformedResponseError("Anthropic fallback did not return a parseable structured response")
        logger.info(
            "fallback_served", extra={"provider": "anthropic", "model": settings.anthropic_fallback_model}
        )
        return parsed

    response = await client.messages.create(
        model=settings.anthropic_fallback_model,
        max_tokens=max_tokens or _DEFAULT_MAX_TOKENS,
        system=instructions,
        messages=[{"role": "user", "content": input_text}],
    )
    logger.info("fallback_served", extra={"provider": "anthropic", "model": settings.anthropic_fallback_model})
    return "".join(block.text for block in response.content if block.type == "text")
