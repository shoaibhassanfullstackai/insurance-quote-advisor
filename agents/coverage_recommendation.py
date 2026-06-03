import json
from typing import Any

from agents.base import BaseAgent
from schemas.agent_outputs import CoverageRecommendationOutput
from utils.llm import call_structured_agent


class CoverageRecommendationAgent(BaseAgent):
    prompt_file = "coverage_recommendation"

    def run(
        self,
        profile: dict[str, Any],
        risk_output: dict[str, Any],
    ) -> tuple[CoverageRecommendationOutput | None, dict[str, Any]]:
        user_content = (
            f"Customer profile:\n{json.dumps(profile, indent=2)}\n\n"
            f"Risk assessment:\n{json.dumps(risk_output, indent=2)}"
        )
        return call_structured_agent(
            self.system_prompt,
            user_content,
            CoverageRecommendationOutput,
        )
