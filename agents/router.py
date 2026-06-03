import json
from typing import Any

from agents.base import BaseAgent
from schemas.agent_outputs import RouterDecision
from utils.llm import call_structured_agent


class RouterAgent(BaseAgent):
    prompt_file = "router"

    def run(
        self,
        user_message: str,
        session_context: dict[str, Any],
    ) -> tuple[RouterDecision | None, dict[str, Any]]:
        user_content = (
            f"User message:\n{user_message}\n\n"
            f"Session state:\n{json.dumps(session_context, indent=2)}"
        )
        return call_structured_agent(
            self.system_prompt,
            user_content,
            RouterDecision,
        )
