import json
from typing import Any

from agents.base import BaseAgent
from schemas.agent_outputs import PricingOutput
from utils.llm import call_structured_agent


class PricingAgent(BaseAgent):
    prompt_file = "pricing"

    def run(
        self,
        profile: dict[str, Any],
        risk_output: dict[str, Any],
        coverage_output: dict[str, Any],
        heuristic_breakdown: dict[str, Any],
    ) -> tuple[PricingOutput | None, dict[str, Any]]:
        user_content = (
            f"Customer profile:\n{json.dumps(profile, indent=2)}\n\n"
            f"Risk assessment:\n{json.dumps(risk_output, indent=2)}\n\n"
            f"Coverage recommendations:\n{json.dumps(coverage_output, indent=2)}\n\n"
            f"PricingHeuristicTool output:\n{json.dumps(heuristic_breakdown, indent=2)}"
        )
        return call_structured_agent(
            self.system_prompt,
            user_content,
            PricingOutput,
        )
