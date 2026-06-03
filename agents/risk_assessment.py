import json
from typing import Any

from agents.base import BaseAgent
from schemas.agent_outputs import RiskAssessmentOutput
from utils.llm import call_structured_agent


class RiskAssessmentAgent(BaseAgent):
    prompt_file = "risk_assessment"

    def run(
        self,
        profile: dict[str, Any],
        tool_breakdown: dict[str, Any],
    ) -> tuple[RiskAssessmentOutput | None, dict[str, Any]]:
        user_content = (
            f"Customer profile:\n{json.dumps(profile, indent=2)}\n\n"
            f"RiskFactorTool output:\n{json.dumps(tool_breakdown, indent=2)}"
        )
        return call_structured_agent(
            self.system_prompt,
            user_content,
            RiskAssessmentOutput,
        )
