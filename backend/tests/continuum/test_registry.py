import pytest
from pydantic import BaseModel

from app.continuum.base_agent import BaseAgent
from app.continuum.exceptions import AgentAlreadyRegisteredError, AgentNotFoundError
from app.continuum.registry import AgentRegistry


class DummyInput(BaseModel):
    value: str


class DummyOutput(BaseModel):
    value: str


class DummyAgent(BaseAgent[DummyInput, DummyOutput]):
    name = "dummy"
    input_schema = DummyInput
    output_schema = DummyOutput

    async def run(self, input_data: DummyInput) -> DummyOutput:
        return DummyOutput(value=input_data.value)


def test_register_and_get():
    registry = AgentRegistry()
    registry.register("dummy", DummyAgent)
    assert registry.get("dummy") is DummyAgent
    assert registry.list_agents() == ["dummy"]


def test_duplicate_registration_raises():
    registry = AgentRegistry()
    registry.register("dummy", DummyAgent)
    with pytest.raises(AgentAlreadyRegisteredError):
        registry.register("dummy", DummyAgent)


def test_overwrite_allows_replacement():
    registry = AgentRegistry()
    registry.register("dummy", DummyAgent)
    registry.register("dummy", DummyAgent, overwrite=True)


def test_unknown_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.get("missing")
