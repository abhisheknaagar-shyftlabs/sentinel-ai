from app.agents.development.prompts import COMPARE_SYSTEM_PROMPT, build_pr_review_prompt
from app.agents.development.schemas import CompareReviewOutput, PRReviewInput
from app.continuum.base_agent import BaseAgent
from app.continuum.registry import register_agent


@register_agent("pr_compare_review")
class CompareReviewAgent(BaseAgent[PRReviewInput, CompareReviewOutput]):
    """Same input shape and prompt-building as PRReviewAgent, but a
    deliberately smaller output schema - see CompareReviewOutput's
    docstring for why. Reuses PRReviewInput/build_pr_review_prompt rather
    than duplicating them; only the system prompt and output schema differ."""

    name = "pr_compare_review"
    description = "A faster, smaller-output PR risk assessment for branch comparisons."
    input_schema = PRReviewInput
    output_schema = CompareReviewOutput

    async def run(self, input_data: PRReviewInput) -> CompareReviewOutput:
        result = await self.continuum_client.run_prompt(
            agent_name=self.name,
            instructions=COMPARE_SYSTEM_PROMPT,
            input_text=build_pr_review_prompt(input_data),
            output_schema=CompareReviewOutput,
        )
        assert isinstance(result, CompareReviewOutput)  # guaranteed by output_schema
        return result
