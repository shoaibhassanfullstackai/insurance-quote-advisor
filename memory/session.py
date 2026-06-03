"""In-memory session: last quote, intermediates, and graph state for follow-ups."""

from dataclasses import dataclass, field
from typing import Any, Optional

from schemas.final_output import FinalQuoteOutput


@dataclass
class SessionMemory:
    thread_id: str = "quote-session-1"
    customer_profile: Optional[dict[str, Any]] = None
    input_warnings: list[str] = field(default_factory=list)
    credit_defaulted: bool = False

    risk_output: Optional[dict[str, Any]] = None
    coverage_output: Optional[dict[str, Any]] = None
    pricing_output: Optional[dict[str, Any]] = None
    validator_output: Optional[dict[str, Any]] = None
    final_quote: Optional[FinalQuoteOutput] = None

    tool_risk_breakdown: Optional[dict[str, Any]] = None
    tool_pricing_breakdown: Optional[dict[str, Any]] = None

    agent_metadata: list[dict[str, Any]] = field(default_factory=list)
    last_user_message: Optional[str] = None
    quote_completed: bool = False
    last_graph_state: Optional[dict[str, Any]] = None

    def snapshot_for_follow_up(self) -> dict[str, Any]:
        return {
            "customer_profile": self.customer_profile,
            "final_quote": self.final_quote.model_dump() if self.final_quote else None,
            "risk_assessment": self.risk_output,
            "coverage_recommendation": self.coverage_output,
            "pricing": self.pricing_output,
            "validator": self.validator_output,
            "tool_risk_breakdown": self.tool_risk_breakdown,
            "tool_pricing_breakdown": self.tool_pricing_breakdown,
            "input_warnings": self.input_warnings,
            "last_graph_state": self.last_graph_state,
        }
