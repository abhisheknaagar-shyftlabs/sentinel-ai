import pytest
from pydantic import BaseModel

from app.continuum.base_agent import BaseAgent
from app.continuum.client import ContinuumClient
from app.continuum.exceptions import AgentNotFoundError
from app.continuum.registry import AgentRegistry


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    text: str


class EchoAgent(BaseAgent[EchoInput, EchoOutput]):
    name = "echo"
    input_schema = EchoInput
    output_schema = EchoOutput

    async def run(self, input_data: EchoInput) -> EchoOutput:
        return EchoOutput(text=input_data.text)


class AlwaysFailsAgent(BaseAgent[EchoInput, EchoOutput]):
    name = "always_fails"
    input_schema = EchoInput
    output_schema = EchoOutput

    async def run(self, input_data: EchoInput) -> EchoOutput:
        raise RuntimeError("permanent failure")


@pytest.fixture
def client():
    registry = AgentRegistry()
    registry.register("echo", EchoAgent)
    registry.register("always_fails", AlwaysFailsAgent)
    return ContinuumClient(registry=registry)


async def test_run_agent_success(client):
    result = await client.run_agent("echo", EchoInput(text="hello"))
    assert result.success is True
    assert result.data.text == "hello"


async def test_run_agent_reports_failure(client):
    result = await client.run_agent("always_fails", EchoInput(text="x"))
    assert result.success is False
    assert "permanent failure" in result.error
    assert result.error_type == "RuntimeError"


async def test_run_agent_unknown_raises(client):
    with pytest.raises(AgentNotFoundError):
        await client.run_agent("missing", EchoInput(text="x"))


async def test_run_workflow_runs_all(client):
    results = await client.run_workflow(["echo", "echo"], EchoInput(text="y"))
    assert len(results) == 2
    assert all(r.success for r in results)


async def test_health_check(client):
    health = await client.health_check()
    assert health["status"] == "ok"
    assert health["runtime"] == "continuum"
    assert "echo" in health["registered_agents"]


async def test_register_agent_dynamic():
    registry = AgentRegistry()
    client = ContinuumClient(registry=registry)
    client.register_agent("echo", EchoAgent)
    result = await client.run_agent("echo", EchoInput(text="dynamic"))
    assert result.data.text == "dynamic"
