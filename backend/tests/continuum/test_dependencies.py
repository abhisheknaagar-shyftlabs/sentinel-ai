from app.continuum.client import ContinuumClient
from app.continuum.dependencies import get_agent_registry, get_continuum_client


def test_agents_are_registered_via_dependencies():
    registry = get_agent_registry()
    names = registry.list_agents()
    assert "pr_review" in names
    assert "root_cause" in names
    assert "executive_summary" in names


def test_get_continuum_client_builds_a_working_client():
    registry = get_agent_registry()
    client = get_continuum_client(registry)
    assert isinstance(client, ContinuumClient)
    assert client.registry is registry
