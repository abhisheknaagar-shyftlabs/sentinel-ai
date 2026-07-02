import pytest
from continuum.agent import AgentExecutionError, AgentResponse, AgentTimeoutError, ResponseStatus
from pydantic import BaseModel

from app.continuum.client import ContinuumClient
from app.continuum.exceptions import ContinuumTimeoutError, ContinuumUnavailableError, MalformedResponseError
from app.continuum.registry import AgentRegistry


class Answer(BaseModel):
    text: str


@pytest.fixture
def client():
    return ContinuumClient(registry=AgentRegistry())


async def test_run_prompt_returns_content_without_schema(client, monkeypatch):
    async def fake_run(self, agent, input_text):
        return AgentResponse(content="hello back", agent_name=agent.name, status=ResponseStatus.SUCCESS)

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    result = await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")
    assert result == "hello back"


async def test_run_prompt_returns_structured_output_with_schema(client, monkeypatch):
    async def fake_run(self, agent, input_text):
        return AgentResponse(
            content="{}",
            agent_name=agent.name,
            status=ResponseStatus.SUCCESS,
            structured_output=Answer(text="parsed"),
        )

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    result = await client.run_prompt(
        agent_name="test", instructions="be nice", input_text="hi", output_schema=Answer
    )
    assert isinstance(result, Answer)
    assert result.text == "parsed"


async def test_run_prompt_raises_malformed_when_schema_requested_but_missing(client, monkeypatch):
    async def fake_run(self, agent, input_text):
        return AgentResponse(
            content="not json",
            agent_name=agent.name,
            status=ResponseStatus.SUCCESS,
            structured_output=None,
            structured_output_error="could not parse JSON",
        )

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    with pytest.raises(MalformedResponseError):
        await client.run_prompt(
            agent_name="test", instructions="be nice", input_text="hi", output_schema=Answer
        )


async def test_run_prompt_maps_error_status(client, monkeypatch):
    async def fake_run(self, agent, input_text):
        return AgentResponse.error_response("boom", agent_name=agent.name)

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    with pytest.raises(ContinuumUnavailableError):
        await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")


async def test_run_prompt_maps_timeout_exception(client, monkeypatch):
    async def fake_run(self, agent, input_text):
        raise AgentTimeoutError("took too long")

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    with pytest.raises(ContinuumTimeoutError):
        await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")


async def test_run_prompt_maps_agent_error(client, monkeypatch):
    async def fake_run(self, agent, input_text):
        raise AgentExecutionError("something broke")

    monkeypatch.setattr(type(client._runner), "run", fake_run)

    with pytest.raises(ContinuumUnavailableError):
        await client.run_prompt(agent_name="test", instructions="be nice", input_text="hi")
