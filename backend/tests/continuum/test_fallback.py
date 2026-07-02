import pytest
from continuum.agent import AgentResponse, AgentTimeoutError, ResponseStatus
from pydantic import BaseModel

from app.continuum.client import ContinuumClient
from app.continuum.exceptions import ContinuumUnavailableError
from app.continuum.registry import AgentRegistry


class Answer(BaseModel):
    text: str


@pytest.fixture
def client():
    return ContinuumClient(registry=AgentRegistry())


async def test_falls_back_to_openai_when_continuum_times_out(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")

    async def fake_run(self, agent, input_text):
        raise AgentTimeoutError("took too long")

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    async def fake_openai(instructions, input_text, output_schema, max_tokens, settings):
        return Answer(text="from openai")

    monkeypatch.setattr("app.continuum.fallback._run_openai", fake_openai)

    result = await client.run_prompt(
        agent_name="test", instructions="be nice", input_text="hi", output_schema=Answer
    )
    assert isinstance(result, Answer)
    assert result.text == "from openai"


async def test_falls_back_to_anthropic_when_openai_fallback_also_fails(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    async def fake_run(self, agent, input_text):
        raise AgentTimeoutError("took too long")

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    async def failing_openai(instructions, input_text, output_schema, max_tokens, settings):
        raise RuntimeError("openai also unavailable")

    async def fake_anthropic(instructions, input_text, output_schema, max_tokens, settings):
        return Answer(text="from anthropic")

    monkeypatch.setattr("app.continuum.fallback._run_openai", failing_openai)
    monkeypatch.setattr("app.continuum.fallback._run_anthropic", fake_anthropic)

    result = await client.run_prompt(
        agent_name="test", instructions="be nice", input_text="hi", output_schema=Answer
    )
    assert result.text == "from anthropic"


async def test_raises_when_no_fallback_provider_succeeds(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")

    async def fake_run(self, agent, input_text):
        raise AgentTimeoutError("took too long")

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    async def failing_openai(instructions, input_text, output_schema, max_tokens, settings):
        raise RuntimeError("openai also unavailable")

    monkeypatch.setattr("app.continuum.fallback._run_openai", failing_openai)

    with pytest.raises(ContinuumUnavailableError):
        await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")


async def test_without_any_fallback_key_original_error_is_unchanged(client, monkeypatch):
    """No OPENAI_API_KEY/ANTHROPIC_API_KEY set - behavior must be identical
    to before this feature existed, not a new error type."""
    from app.continuum.exceptions import ContinuumTimeoutError

    async def fake_run(self, agent, input_text):
        raise AgentTimeoutError("took too long")

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    with pytest.raises(ContinuumTimeoutError):
        await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")


async def test_without_fallback_configured_continuum_gets_the_long_timeout(client, monkeypatch):
    """Regression test: with no fallback key set, the aggressive
    CONTINUUM_FALLBACK_TIMEOUT_SECONDS cutoff must not apply - cutting a
    call off early only makes sense if there's something better to fall
    back to. Without one, it should get the SDK's own long budget instead."""
    from app.continuum.client import _NO_FALLBACK_TIMEOUT_SECONDS

    seen_timeouts = []

    async def fake_run_via_continuum(self, sdk_agent, input_text, output_schema, timeout_seconds):
        seen_timeouts.append(timeout_seconds)
        return "ok"

    monkeypatch.setattr(ContinuumClient, "_run_via_continuum", fake_run_via_continuum)

    result = await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")
    assert result == "ok"
    assert seen_timeouts == [_NO_FALLBACK_TIMEOUT_SECONDS]


async def test_with_fallback_configured_continuum_gets_the_short_timeout(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    seen_timeouts = []

    async def fake_run_via_continuum(self, sdk_agent, input_text, output_schema, timeout_seconds):
        seen_timeouts.append(timeout_seconds)
        return "ok"

    monkeypatch.setattr(ContinuumClient, "_run_via_continuum", fake_run_via_continuum)

    result = await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")
    assert result == "ok"
    from app.config.settings import get_settings

    assert seen_timeouts == [get_settings().continuum_fallback_timeout_seconds]


async def test_continuum_success_never_touches_fallback(client, monkeypatch):
    """A successful Continuum call must not invoke the fallback path at all,
    even if fallback keys happen to be configured."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")

    async def fake_run(self, agent, input_text):
        return AgentResponse(content="direct answer", agent_name=agent.name, status=ResponseStatus.SUCCESS)

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("fallback should not have been invoked")

    monkeypatch.setattr("app.continuum.fallback._run_openai", fail_if_called)

    result = await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")
    assert result == "direct answer"
