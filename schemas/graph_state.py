from __future__ import annotations

from typing import Any, TypedDict


class QuoteGraphState(TypedDict, total=False):
    """LangGraph state passed between workflow nodes."""

    user_message: str
    raw_profile: dict[str, Any] | None
    route: str
    route_reason: str

    input_valid: bool
    input_errors: list[str]
    input_warnings: list[str]
    customer_profile: dict[str, Any] | None
    credit_defaulted: bool

    risk_tool_output: dict[str, Any] | None
    pricing_tool_output: dict[str, Any] | None

    risk_output: dict[str, Any] | None
    coverage_output: dict[str, Any] | None
    pricing_output: dict[str, Any] | None
    validator_output: dict[str, Any] | None
    follow_up_output: dict[str, Any] | None

    validation_rates: list[float]
    guardrail_passed: int
    guardrail_total: int
    consistency_ok: bool
    consistency_issues: list[str]
    error: str | None
    metadata: dict[str, Any]

    quote_result: dict[str, Any] | None
