import json
from typing import Any

from agents.base import BaseAgent
from schemas.agent_outputs import ValidatorOutput
from utils.llm import call_structured_agent


class ValidatorAgent(BaseAgent):
    prompt_file = "validator"

    def run(
        self,
        risk_output: dict[str, Any],
        coverage_output: dict[str, Any],
        pricing_output: dict[str, Any],
    ) -> tuple[ValidatorOutput | None, dict[str, Any]]:
        user_content = (
            f"Risk assessment:\n{json.dumps(risk_output, indent=2)}\n\n"
            f"Coverage:\n{json.dumps(coverage_output, indent=2)}\n\n"
            f"Pricing:\n{json.dumps(pricing_output, indent=2)}"
        )
        return call_structured_agent(
            self.system_prompt,
            user_content,
            ValidatorOutput,
        )
