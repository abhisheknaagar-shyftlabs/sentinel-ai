import pytest

from app.agents.development.pr_review_agent import PRReviewAgent
from app.agents.development.schemas import (
    BreakingChangeAssessment,
    DeploymentConfidence,
    ExecutiveSummary,
    PRReviewInput,
    PRReviewOutput,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    TechnicalDebt,
)
from app.agents.executive.executive_summary_agent import (
    ExecutiveSummaryAgent,
    ExecutiveSummaryInput,
)
from app.agents.production.root_cause_agent import RootCauseAgent
from app.agents.production.schemas import (
    ConfidenceScore,
    IncidentSummary,
    RecoveryPlan,
    RootCause,
    RootCauseAnalysisInput,
    RootCauseAnalysisResponse,
    Severity,
)
from app.integrations.docker.schemas import (
    ContainerDetail,
    ContainerHealthStatus,
    ContainerLogs,
)


class StubContinuumClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def run_prompt(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _sample_review_output() -> PRReviewOutput:
    return PRReviewOutput(
        executive_summary=ExecutiveSummary(summary="Looks solid overall."),
        risk_assessment=RiskAssessment(score=15, level=RiskLevel.LOW, rationale="Small, well-tested change."),
        deployment_confidence=DeploymentConfidence(score=90, rationale="CI is green, scope is narrow."),
        technical_debt=TechnicalDebt(summary="None introduced."),
        breaking_changes=BreakingChangeAssessment(detected=False),
        recommendation=Recommendation.APPROVE,
        recommendation_rationale="Change is small and well covered by tests.",
    )


def _sample_input() -> PRReviewInput:
    return PRReviewInput(
        repository_full_name="octocat/sentinel-ai",
        pr_number=47,
        title="Add retry logic",
        description="Adds retries to the flaky client.",
        base_branch="main",
        head_branch="feature/retries",
        diff="diff --git a/x.py b/x.py\n+retry()\n",
    )


async def test_pr_review_agent_returns_structured_output():
    stub = StubContinuumClient(_sample_review_output())
    agent = PRReviewAgent(continuum_client=stub)

    output = await agent.run(_sample_input())

    assert output.recommendation == Recommendation.APPROVE
    assert output.risk_assessment.score == 15

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["output_schema"] is PRReviewOutput
    assert "47" in call["input_text"]
    assert "Add retry logic" in call["input_text"]


def _sample_rca_input() -> RootCauseAnalysisInput:
    container = ContainerDetail(
        id="abc123def456",
        short_id="abc123def456",
        name="postgres",
        image="postgres:16-alpine",
        status="exited",
        health=ContainerHealthStatus.NONE,
        running=False,
        created_at=None,
        started_at=None,
        restart_count=3,
        exposed_ports=[],
        command="postgres",
        mounted_volumes=[],
        stats=None,
    )
    return RootCauseAnalysisInput(container=container, logs=ContainerLogs(container_id="abc123def456"))


def _sample_rca_output() -> RootCauseAnalysisResponse:
    return RootCauseAnalysisResponse(
        incident_summary=IncidentSummary(
            container_id="abc123def456",
            container_name="postgres",
            observed_state="exited",
            summary="Postgres exited after repeated restarts.",
            severity=Severity.HIGH,
            business_impact="Database unavailable; dependent services will fail.",
        ),
        root_cause=RootCause(
            summary="Out of memory during startup.",
            category="resource_exhaustion",
            confidence=ConfidenceScore(score=70, rationale="Logs show an OOM kill immediately before exit."),
        ),
        recovery_plan=RecoveryPlan(
            auto_restart_safe=False,
            auto_restart_rationale="Restarting without more memory would likely repeat the failure.",
            requires_human_intervention=True,
            human_intervention_reason="Memory limit needs to be raised.",
        ),
    )


async def test_root_cause_agent_returns_structured_output():
    stub = StubContinuumClient(_sample_rca_output())
    agent = RootCauseAgent(continuum_client=stub)

    output = await agent.run(_sample_rca_input())

    assert output.incident_summary.severity == Severity.HIGH
    assert output.recovery_plan.requires_human_intervention is True

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["output_schema"] is RootCauseAnalysisResponse
    assert "postgres" in call["input_text"]


async def test_executive_summary_agent_is_placeholder():
    agent = ExecutiveSummaryAgent(continuum_client=StubContinuumClient(None))
    with pytest.raises(NotImplementedError):
        await agent.run(ExecutiveSummaryInput(workspace_id="ws-1"))
