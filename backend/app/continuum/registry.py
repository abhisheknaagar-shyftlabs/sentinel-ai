from collections.abc import Callable

from app.continuum.base_agent import BaseAgent
from app.continuum.exceptions import AgentAlreadyRegisteredError, AgentNotFoundError


class AgentRegistry:
    """Maps agent names to agent classes. Instantiate your own for isolated
    tests; use get_global_registry() for the process-wide registry that
    the built-in agents register themselves into via @register_agent."""

    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, name: str, agent_cls: type[BaseAgent], *, overwrite: bool = False) -> None:
        if not overwrite and name in self._agents:
            raise AgentAlreadyRegisteredError(f"Agent '{name}' is already registered")
        self._agents[name] = agent_cls

    def get(self, name: str) -> type[BaseAgent]:
        try:
            return self._agents[name]
        except KeyError:
            raise AgentNotFoundError(f"No agent registered under '{name}'") from None

    def list_agents(self) -> list[str]:
        return sorted(self._agents)


_global_registry = AgentRegistry()


def get_global_registry() -> AgentRegistry:
    return _global_registry


def register_agent(name: str) -> Callable[[type[BaseAgent]], type[BaseAgent]]:
    """Class decorator that registers an agent into the global registry
    at import time, e.g. @register_agent("pr_review")."""

    def decorator(agent_cls: type[BaseAgent]) -> type[BaseAgent]:
        _global_registry.register(name, agent_cls)
        return agent_cls

    return decorator
