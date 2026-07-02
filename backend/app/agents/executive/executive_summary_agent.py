from pydantic import BaseModel

from app.continuum.base_agent import BaseAgent
from app.continuum.registry import register_agent


class ExecutiveSummaryInput(BaseModel):
    workspace_id: str
    period_days: int = 30


class ExecutiveSummaryOutput(BaseModel):
    summary: str


@register_agent("executive_summary")
class ExecutiveSummaryAgent(BaseAgent[ExecutiveSummaryInput, ExecutiveSummaryOutput]):
    """Placeholder only — executive intelligence lands in Step 6. Registered
    now so the registry/DI wiring can be validated across all three domains."""

    name = "executive_summary"
    description = "Placeholder — executive summary generation lands in Step 6."
    input_schema = ExecutiveSummaryInput
    output_schema = ExecutiveSummaryOutput

    async def run(self, input_data: ExecutiveSummaryInput) -> ExecutiveSummaryOutput:
        raise NotImplementedError("ExecutiveSummaryAgent is a placeholder for Step 6.")
