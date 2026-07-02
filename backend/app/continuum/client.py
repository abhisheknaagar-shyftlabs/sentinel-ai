import asyncio
import time

from continuum.agent import (
    AgentConfig,
    AgentError,
    AgentMemoryConfig,
    AgentRunner,
    AgentTimeoutError,
    MaxTurnsExceededError,
    ResponseStatus,
)
from continuum.agent import BaseAgent as SDKAgent
from continuum.core import Container, ContainerConfig
from pydantic import BaseModel

from app.config.settings import get_settings
from app.continuum.base_agent import BaseAgent
from app.continuum.cache import get_cached_response, set_cached_response
from app.continuum.exceptions import ContinuumTimeoutError, ContinuumUnavailableError, MalformedResponseError
from app.continuum.fallback import run_with_fallback
from app.continuum.registry import AgentRegistry
from app.continuum.schemas import AgentExecutionResult
from app.core.logging import get_logger

logger = get_logger(__name__)

# Comfortably above the SDK's own worst-case retry budget
# (llm_request_timeout x llm_max_retries, ~240s at this project's settings)
# so this wrapper never preempts Continuum's own exhaustion when there's no
# fallback to cut over to anyway.
_NO_FALLBACK_TIMEOUT_SECONDS = 250

_container: Container | None = None


def _get_container() -> Container:
    """Continuum's DI container, with memory/session/langfuse/temporal disabled —
    Sentinel's PR review calls are single-shot and stateless, so none of that
    infra (Redis/Qdrant/Langfuse/Temporal) is needed just to run a completion."""
    global _container
    if _container is None:
        _container = Container(
            ContainerConfig(enable_memory=False, enable_session=False, enable_langfuse=False)
        )
    return _container


class ContinuumClient:
    """The single entry point for running AI agents. Application services
    call this — never the Continuum SDK, and never a model SDK, directly."""

    def __init__(self, registry: AgentRegistry, runner: AgentRunner | None = None) -> None:
        self.registry = registry
        self._runner = runner or AgentRunner(container=_get_container())

    def register_agent(self, name: str, agent_cls: type[BaseAgent]) -> None:
        self.registry.register(name, agent_cls, overwrite=True)

    async def run_agent(self, agent_name: str, input_data: BaseModel) -> AgentExecutionResult:
        agent_cls = self.registry.get(agent_name)
        agent = agent_cls(continuum_client=self)

        start = time.perf_counter()
        try:
            output = await agent.run(input_data)
        except Exception as exc:  # noqa: BLE001 - any agent/model failure surfaces as a typed result
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "agent_run_failed",
                extra={"agent": agent_name, "error": str(exc), "duration_ms": duration_ms},
            )
            return AgentExecutionResult(
                agent_name=agent_name,
                success=False,
                data=None,
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
            )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("agent_run_succeeded", extra={"agent": agent_name, "duration_ms": duration_ms})
        return AgentExecutionResult(
            agent_name=agent_name, success=True, data=output, duration_ms=duration_ms
        )

    async def run_workflow(
        self, agent_names: list[str], input_data: BaseModel
    ) -> list[AgentExecutionResult]:
        """Runs each named agent sequentially against the same input. This is
        a minimal foundation — DAG-based multi-agent orchestration is future work."""
        return [await self.run_agent(name, input_data) for name in agent_names]

    async def run_prompt(
        self,
        *,
        agent_name: str,
        instructions: str,
        input_text: str,
        output_schema: type[BaseModel] | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> BaseModel | str:
        """The one place that touches the Continuum SDK's own agent runtime.
        Domain agents (PRReviewAgent, etc.) call this instead of any model SDK."""
        cached = await get_cached_response(agent_name, instructions, input_text, output_schema)
        if cached is not None:
            return cached

        sdk_agent_kwargs: dict = {
            "name": agent_name,
            "instructions": instructions,
            "output_schema": output_schema,
            "memory_config": AgentMemoryConfig(search_memories=False, store_memories=False),
        }
        # Omit rather than pass None - BaseAgent's dataclass default (settings.default_llm_model)
        # only applies when the field isn't supplied at all.
        if model:
            sdk_agent_kwargs["model"] = model
        if max_tokens:
            sdk_agent_kwargs["config"] = AgentConfig(max_tokens=max_tokens)

        sdk_agent = SDKAgent(**sdk_agent_kwargs)
        settings = get_settings()
        has_fallback = bool(settings.openai_api_key or settings.anthropic_api_key)
        # Only cut Continuum off early if there's actually something better
        # to fall back to. With no fallback configured, an aggressive
        # cutoff just fails calls that would have succeeded given the SDK's
        # own (much longer) retry budget - worse than waiting.
        timeout_seconds = settings.continuum_fallback_timeout_seconds if has_fallback else _NO_FALLBACK_TIMEOUT_SECONDS

        try:
            result = await self._run_via_continuum(sdk_agent, input_text, output_schema, timeout_seconds)
        except (TimeoutError, ContinuumTimeoutError, ContinuumUnavailableError, MalformedResponseError) as exc:
            if not has_fallback:
                raise
            # Any Continuum-side failure - not just slowness - falls through
            # to a direct provider call. A demo needs a result, not a wait.
            logger.warning(
                "continuum_failed_falling_back",
                extra={"agent": agent_name, "error": str(exc), "error_type": type(exc).__name__},
            )
            result = await run_with_fallback(instructions, input_text, output_schema, max_tokens, settings, exc)

        # Only successful results are cached - a failure shouldn't get
        # "stuck" for the cache TTL, since the same request might genuinely
        # succeed on a later, unrelated attempt (transient gateway load).
        await set_cached_response(agent_name, instructions, input_text, output_schema, result)
        return result

    async def _run_via_continuum(
        self,
        sdk_agent: SDKAgent,
        input_text: str,
        output_schema: type[BaseModel] | None,
        timeout_seconds: int,
    ) -> BaseModel | str:
        try:
            response = await asyncio.wait_for(self._runner.run(sdk_agent, input_text), timeout=timeout_seconds)
        except AgentTimeoutError as exc:
            raise ContinuumTimeoutError(str(exc)) from exc
        except MaxTurnsExceededError as exc:
            raise ContinuumUnavailableError(f"Continuum agent exceeded its turn limit: {exc}") from exc
        except AgentError as exc:
            raise ContinuumUnavailableError(str(exc)) from exc

        if response.status == ResponseStatus.ERROR or response.error:
            raise ContinuumUnavailableError(response.error or "Continuum agent run failed")

        if output_schema is not None:
            if response.structured_output is None:
                raise MalformedResponseError(
                    response.structured_output_error
                    or "Continuum did not return a response matching the expected schema"
                )
            return response.structured_output

        return response.content

    async def health_check(self) -> dict:
        return {
            "status": "ok",
            "runtime": "continuum",
            "registered_agents": self.registry.list_agents(),
        }
