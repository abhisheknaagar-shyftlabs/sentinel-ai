import pytest

from app.continuum.client import ContinuumClient
from app.continuum.exceptions import MalformedResponseError
from app.integrations.docker.client import DockerClient
from app.integrations.docker.exceptions import DockerContainerNotFoundError
from app.agents.production.schemas import (
    ConfidenceScore,
    IncidentSummary,
    RecoveryPlan,
    RootCause,
    RootCauseAnalysisResponse,
    Severity,
)
from tests.test_github import _register_and_login

FULL_ATTRS = {
    "State": {"Status": "exited", "Running": False, "StartedAt": "0001-01-01T00:00:00Z"},
    "Created": "2026-07-01T09:59:00.000000000Z",
    "RestartCount": 3,
    "Config": {"Image": "postgres:16-alpine", "Cmd": ["postgres"]},
    "NetworkSettings": {"Ports": {}},
    "Mounts": [],
}

SAMPLE_RCA = RootCauseAnalysisResponse(
    incident_summary=IncidentSummary(
        container_id="abc123def456",
        container_name="postgres",
        observed_state="exited",
        summary="Postgres exited after repeated restarts.",
        severity=Severity.HIGH,
        business_impact="Database unavailable.",
    ),
    root_cause=RootCause(
        summary="Out of memory during startup.",
        category="resource_exhaustion",
        confidence=ConfidenceScore(score=70, rationale="OOM kill in logs."),
    ),
    recovery_plan=RecoveryPlan(
        auto_restart_safe=False,
        auto_restart_rationale="Would likely repeat the failure.",
        requires_human_intervention=True,
    ),
)


class FakeContainer:
    def __init__(self, container_id="abc123def456"):
        self.id = container_id
        self.short_id = container_id[:12]
        self.name = "postgres"
        self.status = "exited"
        self.attrs = FULL_ATTRS

    def stats(self, stream=False):
        return {"cpu_stats": {}, "precpu_stats": {}, "memory_stats": {}, "networks": {}, "blkio_stats": {}}

    def logs(self, tail, timestamps):
        return b"2026-07-02T10:00:00.000000000Z FATAL: out of memory\n"


def _patch_docker(monkeypatch, container=None):
    async def fake_get_container(self, container_id):
        if container is None:
            raise DockerContainerNotFoundError(container_id)
        return container

    async def fake_container_stats(self, container_id):
        return container.stats(stream=False)

    async def fake_container_logs(self, container_id, tail, timestamps):
        return container.logs(tail, timestamps)

    monkeypatch.setattr(DockerClient, "get_container", fake_get_container)
    monkeypatch.setattr(DockerClient, "container_stats", fake_container_stats)
    monkeypatch.setattr(DockerClient, "container_logs", fake_container_logs)


async def test_analyze_container_returns_structured_diagnosis(client, monkeypatch):
    _patch_docker(monkeypatch, container=FakeContainer())

    async def fake_run_prompt(self, **kwargs):
        assert kwargs["output_schema"] is RootCauseAnalysisResponse
        return SAMPLE_RCA

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/v1/docker/containers/abc123def456/analyze", headers=headers
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["incident_summary"]["severity"] == "high"
    assert data["recovery_plan"]["requires_human_intervention"] is True


async def test_analyze_container_not_found_returns_404(client, monkeypatch):
    _patch_docker(monkeypatch, container=None)
    headers = await _register_and_login(client)
    response = await client.post("/api/v1/docker/containers/missing/analyze", headers=headers)
    assert response.status_code == 404


async def test_analyze_container_malformed_ai_response_maps_to_422(client, monkeypatch):
    _patch_docker(monkeypatch, container=FakeContainer())

    async def fake_run_prompt(self, **kwargs):
        raise MalformedResponseError("could not parse JSON")

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/v1/docker/containers/abc123def456/analyze", headers=headers
    )
    assert response.status_code == 422
    assert response.json()["success"] is False


async def test_analyze_container_never_restarts(client, monkeypatch):
    """The analyze flow must never call restart - diagnosis only."""
    _patch_docker(monkeypatch, container=FakeContainer())

    def fail_if_called(*args, **kwargs):
        raise AssertionError("restart_container must never be called by analyze")

    monkeypatch.setattr(DockerClient, "restart_container", fail_if_called)

    async def fake_run_prompt(self, **kwargs):
        return SAMPLE_RCA

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/v1/docker/containers/abc123def456/analyze", headers=headers
    )
    assert response.status_code == 200


async def test_unauthenticated_analyze_rejected(client):
    response = await client.post("/api/v1/docker/containers/abc123def456/analyze")
    assert response.status_code == 401
