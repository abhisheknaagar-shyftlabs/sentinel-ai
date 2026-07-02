from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.continuum.client import ContinuumClient

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Every AI capability in Sentinel is implemented as an agent that
    subclasses this. Agents never touch an LLM SDK or the Continuum SDK's
    own BaseAgent/AgentRunner directly — they call ContinuumClient."""

    name: ClassVar[str]
    description: ClassVar[str] = ""
    input_schema: ClassVar[type[BaseModel]]
    output_schema: ClassVar[type[BaseModel]]

    def __init__(self, continuum_client: "ContinuumClient") -> None:
        self.continuum_client = continuum_client

    @abstractmethod
    async def run(self, input_data: InputT) -> OutputT: ...
