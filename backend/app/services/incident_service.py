import uuid

from app.agents.production.schemas import IncidentDiagnosis, Severity
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.integrations.docker.service import DockerMonitoringService
from app.integrations.slack.client import SlackClient
from app.models.incident import Incident, IncidentContainer, IncidentEvent
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreateRequest, IncidentEventType, IncidentStatus
from app.services.root_cause_service import RootCauseAnalysisService
from app.utils.time import utc_now

logger = get_logger(__name__)

# Collapses the RCA agent's 4-level Severity into the 3-level scale the
# incident Slack notification uses (high and critical both read as "3" -
# the message text still spells out the original label alongside the number).
_SEVERITY_LEVEL: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 3,
}
_SEVERITY_EMOJI = {1: "🟡", 2: "🟠", 3: "🔴"}


class IncidentService:
    """The canonical production object. Never talks to Docker or Continuum
    directly for analysis/recovery - it only ever calls the existing
    DockerMonitoringService and RootCauseAnalysisService, treating both as
    black boxes. No AI logic and no restart logic are duplicated here."""

    def __init__(
        self,
        incidents: IncidentRepository,
        docker_service: DockerMonitoringService,
        root_cause_service: RootCauseAnalysisService,
        slack_client: SlackClient,
    ) -> None:
        self.incidents = incidents
        self.docker_service = docker_service
        self.root_cause_service = root_cause_service
        self.slack_client = slack_client

    async def create_incident(self, payload: IncidentCreateRequest) -> Incident:
        incident = Incident(
            title=payload.title,
            summary=payload.summary or "",
            severity=payload.severity.value,
            status=IncidentStatus.OPEN.value,
            recovery_executed=False,
        )

        for container_id in payload.container_ids:
            container = await self.docker_service.get_container(container_id)
            incident.affected_containers.append(
                IncidentContainer(
                    container_id=container.id,
                    container_name=container.name,
                    image=container.image,
                )
            )

        self._add_event(incident, IncidentEventType.INCIDENT_CREATED, f"Incident created: {payload.title}")
        await self.incidents.create(incident)
        logger.info("incident_created", extra={"incident_id": str(incident.id), "title": payload.title})
        return incident

    async def list_incidents(self) -> list[Incident]:
        return await self.incidents.list_all()

    async def get_incident(self, incident_id: uuid.UUID) -> Incident:
        incident = await self.incidents.get_by_id_with_relations(incident_id)
        if incident is None:
            raise NotFoundError("Incident not found")
        return incident

    async def analyze_incident(self, incident_id: uuid.UUID) -> Incident:
        incident = await self.get_incident(incident_id)
        if not incident.affected_containers:
            raise ConflictError("Incident has no affected containers to analyze")

        incident.status = IncidentStatus.INVESTIGATING.value
        self._add_event(incident, IncidentEventType.ANALYSIS_STARTED, "Root cause analysis started")
        await self.incidents.session.flush()

        primary = incident.affected_containers[0]
        try:
            analysis = await self.root_cause_service.diagnose_incident(primary.container_id)
        except Exception:
            incident.status = IncidentStatus.OPEN.value
            self._add_event(incident, IncidentEventType.ANALYSIS_FAILED, "Root cause analysis failed")
            await self.incidents.session.flush()
            raise

        incident.root_cause_summary = analysis.summary
        incident.root_cause_confidence = analysis.confidence
        incident.recovery_recommendation = analysis.auto_restart_rationale
        incident.status = (
            IncidentStatus.RECOVERY_AVAILABLE.value
            if analysis.auto_restart_safe
            else IncidentStatus.ANALYZED.value
        )
        self._add_event(
            incident,
            IncidentEventType.ANALYSIS_COMPLETED,
            f"Root cause identified: {analysis.summary}",
        )
        await self.incidents.session.flush()
        logger.info(
            "incident_analyzed",
            extra={"incident_id": str(incident.id), "status": incident.status},
        )
        await self._notify_slack(incident, analysis)
        return incident

    async def recover_incident(self, incident_id: uuid.UUID) -> Incident:
        incident = await self.get_incident(incident_id)
        if incident.status != IncidentStatus.RECOVERY_AVAILABLE.value:
            raise ConflictError(f"Incident is not ready for recovery (status: {incident.status})")
        if not incident.affected_containers:
            raise ConflictError("Incident has no affected containers to recover")

        primary = incident.affected_containers[0]
        self._add_event(
            incident, IncidentEventType.RECOVERY_STARTED, f"Restarting {primary.container_name}"
        )
        await self.incidents.session.flush()

        try:
            await self.docker_service.restart_container(primary.container_id)
        except Exception as exc:
            self._add_event(incident, IncidentEventType.RECOVERY_FAILED, f"Restart failed: {exc}")
            await self.incidents.session.flush()
            raise

        incident.recovery_executed = True
        incident.recovery_result = f"Restarted {primary.container_name} successfully"
        incident.status = IncidentStatus.RESOLVED.value
        incident.resolved_at = utc_now()
        self._add_event(incident, IncidentEventType.RECOVERY_COMPLETED, incident.recovery_result)
        self._add_event(incident, IncidentEventType.RESOLVED, "Incident resolved")
        await self.incidents.session.flush()
        logger.info("incident_resolved", extra={"incident_id": str(incident.id)})
        return incident

    @staticmethod
    def _add_event(incident: Incident, event_type: IncidentEventType, message: str) -> None:
        incident.events.append(IncidentEvent(event_type=event_type.value, message=message))

    async def _notify_slack(self, incident: Incident, analysis: IncidentDiagnosis) -> None:
        """Best-effort only - a Slack outage or missing webhook must never
        fail an incident analysis that otherwise succeeded. Mirrors the AWS
        cost integration's convention of degrading quietly instead of
        crashing when an optional external dependency isn't available."""
        if not self.slack_client.is_configured:
            return

        text, blocks = self._build_slack_message(incident, analysis)
        try:
            await self.slack_client.post_message(text, blocks)
        except Exception as exc:
            logger.warning(
                "slack_notification_failed",
                extra={"incident_id": str(incident.id), "error": str(exc)},
            )

    @staticmethod
    def _build_slack_message(incident: Incident, analysis: IncidentDiagnosis) -> tuple[str, list[dict]]:
        severity = analysis.severity
        level = _SEVERITY_LEVEL[severity]
        emoji = _SEVERITY_EMOJI[level]
        container_name = incident.affected_containers[0].container_name

        actions = "\n".join(f"• {action}" for action in analysis.recommended_actions)
        if incident.status == IncidentStatus.RECOVERY_AVAILABLE.value:
            apply_line = (
                f"✅ *Safe to auto-recover.* `POST /api/v1/incidents/{incident.id}/recover` "
                "to apply it."
            )
        else:
            apply_line = (
                "⚠️ *Requires human intervention*: "
                f"{analysis.human_intervention_reason or 'see recommended actions above'}."
            )

        text = (
            f"{emoji} Incident: {incident.title} ({container_name})\n"
            f"Severity: {level}/3 ({severity.value})\n"
            f"{analysis.summary}"
        )
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *Incident: {incident.title}* (`{container_name}`)\n"
                        f"*Severity:* {level}/3 ({severity.value})"
                    ),
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Root cause:*\n{analysis.summary}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommended actions:*\n{actions or 'None'}"},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": apply_line}},
        ]
        return text, blocks
