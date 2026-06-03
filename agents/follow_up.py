import json
from typing import Any

from agents.base import BaseAgent
from schemas.final_output import FollowUpResponse
from utils.llm import call_structured_agent


class FollowUpAgent(BaseAgent):
    prompt_file = "follow_up"

    def run(
        self,
        question: str,
        session_snapshot: dict[str, Any],
    ) -> tuple[FollowUpResponse | None, dict[str, Any]]:
        user_content = (
            f"User question:\n{question}\n\n"
            f"Session context:\n{json.dumps(session_snapshot, indent=2)}"
        )
        return call_structured_agent(
            self.system_prompt,
            user_content,
            FollowUpResponse,
        )
