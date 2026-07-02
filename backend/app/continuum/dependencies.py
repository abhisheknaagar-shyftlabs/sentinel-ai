from fastapi import Depends

import app.agents  # noqa: F401 - importing triggers @register_agent side effects
from app.continuum.client import ContinuumClient
from app.continuum.registry import AgentRegistry, get_global_registry


def get_agent_registry() -> AgentRegistry:
    return get_global_registry()


def get_continuum_client(registry: AgentRegistry = Depends(get_agent_registry)) -> ContinuumClient:
    return ContinuumClient(registry=registry)
