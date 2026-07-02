from app.agents.production.schemas import IncidentDiagnosis, Severity
from app.config.settings import get_settings
from app.continuum.client import ContinuumClient
from app.integrations.docker.client import DockerClient
from app.integrations.docker.exceptions import DockerContainerNotFoundError
from app.integrations.slack.client import SlackClient
from tests.test_github import _register_and_login
from tests.test_root_cause import FakeContainer

CONTAINER = FakeContainer("abc123def456")

SAMPLE_DIAGNOSIS = IncidentDiagnosis(
    summary="Postgres exited after repeated restarts.",
    severity=Severity.HIGH,
    confidence=70,
    recommended_actions=["Increase memory limit", "Check for connection leaks"],
    auto_restart_safe=False,
    auto_restart_rationale="Would likely repeat the failure.",
    requires_human_intervention=True,
)


def _patch_docker(monkeypatch, container=None):
    async def fake_get_container(self, container_id):
        if container is None:
            raise DockerContainerNotFoundError(container_id)
        return container

    async def fake_container_stats(self, container_id):
        return container.stats(stream=False)

    async def fake_container_logs(self, container_id, tail, timestamps):
        return container.logs(tail, timestamps)

    restart_calls = []

    async def fake_restart_container(self, container_id, timeout=10):
        restart_calls.append(container_id)

    monkeypatch.setattr(DockerClient, "get_container", fake_get_container)
    monkeypatch.setattr(DockerClient, "container_stats", fake_container_stats)
    monkeypatch.setattr(DockerClient, "container_logs", fake_container_logs)
    monkeypatch.setattr(DockerClient, "restart_container", fake_restart_container)
    return restart_calls


def _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS):
    async def fake_run_prompt(self, **kwargs):
        return response

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)


async def test_create_list_and_get_incident(client, monkeypatch):
    _patch_docker(monkeypatch, container=CONTAINER)
    headers = await _register_and_login(client)

    create_response = await client.post(
        "/api/v1/incidents",
        json={"title": "Postgres down", "severity": "high", "container_ids": ["abc123def456"]},
        headers=headers,
    )
    assert create_response.status_code == 201
    incident = create_response.json()["data"]
    assert incident["status"] == "open"
    assert incident["affected_containers"][0]["container_name"] == "postgres"
    assert incident["events"][0]["event_type"] == "incident_created"

    list_response = await client.get("/api/v1/incidents", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    get_response = await client.get(f"/api/v1/incidents/{incident['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == incident["id"]


async def test_create_incident_missing_container_returns_404(client, monkeypatch):
    _patch_docker(monkeypatch, container=None)
    headers = await _register_and_login(client)

    response = await client.post(
        "/api/v1/incidents",
        json={"title": "X", "container_ids": ["missing"]},
        headers=headers,
    )
    assert response.status_code == 404


async def test_full_incident_lifecycle_via_api(client, monkeypatch):
    restart_calls = _patch_docker(monkeypatch, container=CONTAINER)
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)
    headers = await _register_and_login(client)

    create_response = await client.post(
        "/api/v1/incidents",
        json={"title": "Postgres down", "container_ids": ["abc123def456"]},
        headers=headers,
    )
    incident_id = create_response.json()["data"]["id"]

    analyze_response = await client.post(f"/api/v1/incidents/{incident_id}/analyze", headers=headers)
    assert analyze_response.status_code == 200
    analyzed = analyze_response.json()["data"]
    assert analyzed["root_cause_summary"] == SAMPLE_DIAGNOSIS.summary
    # SAMPLE_DIAGNOSIS has auto_restart_safe=False, so it should require human intervention
    assert analyzed["status"] == "analyzed"

    recover_response = await client.post(f"/api/v1/incidents/{incident_id}/recover", headers=headers)
    assert recover_response.status_code == 409  # not recovery_available yet
    assert restart_calls == []


async def test_recover_after_safe_analysis_restarts_and_resolves(client, monkeypatch):
    restart_calls = _patch_docker(monkeypatch, container=CONTAINER)

    safe_response = SAMPLE_DIAGNOSIS.model_copy(
        update={"auto_restart_safe": True, "requires_human_intervention": False}
    )
    _patch_continuum(monkeypatch, response=safe_response)
    headers = await _register_and_login(client)

    create_response = await client.post(
        "/api/v1/incidents",
        json={"title": "Postgres down", "container_ids": ["abc123def456"]},
        headers=headers,
    )
    incident_id = create_response.json()["data"]["id"]

    await client.post(f"/api/v1/incidents/{incident_id}/analyze", headers=headers)
    recover_response = await client.post(f"/api/v1/incidents/{incident_id}/recover", headers=headers)

    assert recover_response.status_code == 200
    resolved = recover_response.json()["data"]
    assert resolved["status"] == "resolved"
    assert resolved["recovery_executed"] is True
    assert restart_calls == ["abc123def456"]


async def test_unauthenticated_incident_requests_rejected(client):
    response = await client.get("/api/v1/incidents")
    assert response.status_code == 401


async def test_analyze_incident_posts_slack_notification_when_configured(client, monkeypatch):
    _patch_docker(monkeypatch, container=CONTAINER)
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    get_settings.cache_clear()

    posted = []

    async def fake_post_message(self, text, blocks=None):
        posted.append((text, blocks))

    monkeypatch.setattr(SlackClient, "post_message", fake_post_message)
    headers = await _register_and_login(client)

    create_response = await client.post(
        "/api/v1/incidents",
        json={"title": "Postgres down", "container_ids": ["abc123def456"]},
        headers=headers,
    )
    incident_id = create_response.json()["data"]["id"]

    analyze_response = await client.post(f"/api/v1/incidents/{incident_id}/analyze", headers=headers)
    assert analyze_response.status_code == 200
    assert len(posted) == 1
    text, blocks = posted[0]
    assert "Postgres down" in text
    assert SAMPLE_DIAGNOSIS.summary in text
    assert blocks is not None


async def test_analyze_incident_succeeds_even_when_slack_notification_fails(client, monkeypatch):
    _patch_docker(monkeypatch, container=CONTAINER)
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    get_settings.cache_clear()

    async def fake_post_message(self, text, blocks=None):
        raise RuntimeError("Slack is down")

    monkeypatch.setattr(SlackClient, "post_message", fake_post_message)
    headers = await _register_and_login(client)

    create_response = await client.post(
        "/api/v1/incidents",
        json={"title": "Postgres down", "container_ids": ["abc123def456"]},
        headers=headers,
    )
    incident_id = create_response.json()["data"]["id"]

    analyze_response = await client.post(f"/api/v1/incidents/{incident_id}/analyze", headers=headers)
    assert analyze_response.status_code == 200
    assert analyze_response.json()["data"]["status"] == "analyzed"


async def test_analyze_incident_skips_slack_when_not_configured(client, monkeypatch):
    _patch_docker(monkeypatch, container=CONTAINER)
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)

    posted = []

    async def fake_post_message(self, text, blocks=None):
        posted.append((text, blocks))

    monkeypatch.setattr(SlackClient, "post_message", fake_post_message)
    headers = await _register_and_login(client)

    create_response = await client.post(
        "/api/v1/incidents",
        json={"title": "Postgres down", "container_ids": ["abc123def456"]},
        headers=headers,
    )
    incident_id = create_response.json()["data"]["id"]

    analyze_response = await client.post(f"/api/v1/incidents/{incident_id}/analyze", headers=headers)
    assert analyze_response.status_code == 200
    assert posted == []
