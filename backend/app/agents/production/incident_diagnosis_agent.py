from app.agents.production.prompts import INCIDENT_DIAGNOSIS_SYSTEM_PROMPT, build_rca_prompt
from app.agents.production.schemas import IncidentDiagnosis, RootCauseAnalysisInput
from app.continuum.base_agent import BaseAgent
from app.continuum.registry import register_agent


@register_agent("incident_diagnosis")
class IncidentDiagnosisAgent(BaseAgent[RootCauseAnalysisInput, IncidentDiagnosis]):
    """A faster, smaller-output root cause diagnosis for the health monitor's
    automatic incident path - see IncidentDiagnosis's docstring. Same input
    as RootCauseAgent (never talks to Docker itself); only the prompt and
    output schema are leaner."""

    name = "incident_diagnosis"
    description = "A faster, smaller-output container diagnosis for automatically opened incidents."
    input_schema = RootCauseAnalysisInput
    output_schema = IncidentDiagnosis

    async def run(self, input_data: RootCauseAnalysisInput) -> IncidentDiagnosis:
        result = await self.continuum_client.run_prompt(
            agent_name=self.name,
            instructions=INCIDENT_DIAGNOSIS_SYSTEM_PROMPT,
            input_text=build_rca_prompt(input_data),
            output_schema=IncidentDiagnosis,
        )
        assert isinstance(result, IncidentDiagnosis)
        return result
