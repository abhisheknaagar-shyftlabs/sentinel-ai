from app.agents.development.prompts import SYSTEM_PROMPT, build_pr_review_prompt
from app.agents.development.schemas import PRReviewInput, PRReviewOutput
from app.continuum.base_agent import BaseAgent
from app.continuum.registry import register_agent


@register_agent("pr_review")
class PRReviewAgent(BaseAgent[PRReviewInput, PRReviewOutput]):
    """The reference pattern for AI capabilities in Sentinel: gather typed
    input from an existing service (never re-fetch data an agent shouldn't
    own), build a prompt in a dedicated module, run it through Continuum,
    and return a fully typed result. Future agents (root cause, executive
    summary, recovery recommendation) should follow this exact shape."""

    name = "pr_review"
    description = "Performs a senior-engineer-level review of a pull request and returns a structured assessment."
    input_schema = PRReviewInput
    output_schema = PRReviewOutput

    async def run(self, input_data: PRReviewInput) -> PRReviewOutput:
        result = await self.continuum_client.run_prompt(
            agent_name=self.name,
            instructions=SYSTEM_PROMPT,
            input_text=build_pr_review_prompt(input_data),
            output_schema=PRReviewOutput,
        )
        assert isinstance(result, PRReviewOutput)  # guaranteed by output_schema
        return result
