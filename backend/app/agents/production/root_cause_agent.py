from app.agents.production.prompts import SYSTEM_PROMPT, build_rca_prompt
from app.agents.production.schemas import RootCauseAnalysisInput, RootCauseAnalysisResponse
from app.continuum.base_agent import BaseAgent
from app.continuum.registry import register_agent


@register_agent("root_cause")
class RootCauseAgent(BaseAgent[RootCauseAnalysisInput, RootCauseAnalysisResponse]):
    """Diagnoses why a container is failing using live Docker state and logs
    already collected by DockerMonitoringService - this agent never talks to
    Docker itself. Same reference pattern as PRReviewAgent."""

    name = "root_cause"
    description = "Diagnoses the likely root cause of a container failure from live metadata, stats, and logs."
    input_schema = RootCauseAnalysisInput
    output_schema = RootCauseAnalysisResponse

    async def run(self, input_data: RootCauseAnalysisInput) -> RootCauseAnalysisResponse:
        result = await self.continuum_client.run_prompt(
            agent_name=self.name,
            instructions=SYSTEM_PROMPT,
            input_text=build_rca_prompt(input_data),
            output_schema=RootCauseAnalysisResponse,
        )
        assert isinstance(result, RootCauseAnalysisResponse)  # guaranteed by output_schema
        return result
